"""Reference Reels: measure what makes a Reel Swati likes work (pacing, hook, captions, loudness) so
Claude can learn the grammar, never copy the content. The video itself is never committed."""
import json, os, re, subprocess
from .media import probe, extract_wav, transcribe, contact_sheet
from .util import run

def scene_cuts(video, thresh=0.32):
    r = subprocess.run(["ffmpeg", "-i", video, "-vf", f"select='gt(scene,{thresh})',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [round(float(m), 3) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)]

def loudness(video):
    r = subprocess.run(["ffmpeg", "-i", video, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None

def metrics(info):
    """Engagement numbers from a yt-dlp info dict (saves are never public; shares rarely are)."""
    if not info: return {}
    g = lambda k: info.get(k)
    v = g("view_count") or 0
    m = {"title": g("title"), "uploader": g("uploader") or g("channel"), "followers": g("channel_follower_count"),
         "upload_date": g("upload_date"), "views": g("view_count"), "likes": g("like_count"),
         "comments": g("comment_count"), "shares": g("repost_count"), "platform": g("extractor_key"),
         "url": g("webpage_url") or g("original_url")}
    if v:
        if m["likes"] is not None: m["like_rate"] = round(m["likes"] / v, 4)
        if m["comments"] is not None: m["comment_rate"] = round(m["comments"] / v, 5)
        if m["followers"]: m["views_per_follower"] = round(v / m["followers"], 2)
    return {k: x for k, x in m.items() if x is not None}

def analyse(video, out, url=None, model="small.en", info=None):
    os.makedirs(out, exist_ok=True)
    meta = probe(video)
    d = meta["duration"]
    cuts = scene_cuts(video)
    shots = [b - a for a, b in zip([0.0] + cuts, cuts + [d])]
    words = []
    if meta["has_audio"]:
        wav = os.path.join(out, "_a.wav"); extract_wav(video, wav)
        try: words, _, _ = transcribe(wav, model)
        finally: os.remove(wav)
    speech = sum(w["e"] - w["s"] for w in words)
    first3 = " ".join(w["w"] for w in words if w["s"] < 3.0)
    res = {
        "url": url, "engagement": metrics(info), "duration": round(d, 2), "size": [meta["width"], meta["height"]], "fps": meta["fps"],
        "cuts": len(cuts), "cut_times": cuts[:80],
        "avg_shot_s": round(sum(shots) / len(shots), 2) if shots else None,
        "shortest_shot_s": round(min(shots), 2) if shots else None,
        "cuts_in_first_3s": sum(1 for c in cuts if c < 3.0),
        "words": len(words), "words_per_sec": round(len(words) / d, 2) if d else None,
        "speech_ratio": round(speech / d, 2) if d else None,
        "hook_words_first_3s": first3,
        "first_word_at": words[0]["s"] if words else None,
        "loudness_lufs": loudness(video),
    }
    json.dump(res, open(os.path.join(out, "analysis.json"), "w"), indent=2)
    with open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8") as f:
        line, t0 = [], 0.0
        for w in words:
            if not line: t0 = w["s"]
            line.append(w["w"])
            if len(line) >= 12 or w["w"].endswith((".", "?", "!")):
                f.write(f"[{t0:6.2f}] " + " ".join(line) + "\n"); line = []
        if line: f.write(f"[{t0:6.2f}] " + " ".join(line) + "\n")
    # the hook, frame by frame (first 3 s at 4 fps) and the whole Reel at a glance
    contact_sheet(video, os.path.join(out, "hook.jpg"), n=12, width=240, cols=6, start=0.0, end=min(3.0, d))
    contact_sheet(video, os.path.join(out, "frames.jpg"), n=min(30, max(12, int(d / 1.5))), width=200, cols=6)
    return res
