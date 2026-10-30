"""Media prep that doesn't depend on the topic: probing, transcription, the edit-friendly proxy,
contact sheets. Used by `prepare` on GitHub (and by the self-test)."""
import glob, json, os, re, shutil, subprocess, wave
from .util import run, ReelError, font_path

def probe(path):
    j = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]))
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if v is None: raise ReelError(f"{path} has no video stream")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd: rot = int(float(sd["rotation"]))
    rot = int(float(v.get("tags", {}).get("rotate", rot) or rot))
    if abs(rot) in (90, 270): w, h = h, w
    num, den = (v.get("avg_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den) if float(den or 0) else 30.0
    return {"width": w, "height": h, "fps": round(fps, 3), "codec": v.get("codec_name"),
            "transfer": v.get("color_transfer", ""), "duration": float(j["format"]["duration"]),
            "has_audio": a is not None, "size_mb": round(int(j["format"].get("size", 0)) / 1e6, 1)}

def extract_wav(video, wav, rate=16000):
    run(["ffmpeg", "-y", "-i", video, "-vn", "-ac", "1", "-ar", str(rate), "-sample_fmt", "s16", wav])

def load_wav_float(wav):
    """16-bit mono wav -> float32 numpy array (bypasses PyAV, whose versions clash with faster-whisper)."""
    import numpy as np
    with wave.open(wav, "rb") as f:
        data = f.readframes(f.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

def volume_stats(wav):
    vd = subprocess.run(["ffmpeg", "-i", wav, "-af", "volumedetect", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    mean = float((re.search(r"mean_volume: (-?[\d.]+)", vd) or [0, -99])[1])
    peak = float((re.search(r"max_volume: (-?[\d.]+)", vd) or [0, -99])[1])
    return mean, peak

def transcribe(wav, model=None, glossary=None):
    """Word-level transcript: [{id, w, s, e, p}]. Drops Whisper's invented words over trailing silence."""
    from faster_whisper import WhisperModel
    name = model or os.environ.get("WHISPER_MODEL", "medium.en")
    prompt = None
    if glossary and os.path.exists(glossary):
        prompt = open(glossary, encoding="utf-8").read().strip()[:800]
    wm = WhisperModel(name, device="cpu", compute_type="int8")
    segs, info = wm.transcribe(load_wav_float(wav), word_timestamps=True, beam_size=5,
                               initial_prompt=prompt, vad_filter=True,
                               vad_parameters={"min_silence_duration_ms": 300})
    words = []
    for sg in segs:
        for w in sg.words or []:
            t = w.word.strip()
            if not t: continue
            words.append({"w": t, "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)})
    for i, w in enumerate(words): w["id"] = f"w{i}"
    return words, name, info.language

def write_transcript(words, out, meta):
    json.dump({"model": meta.get("model"), "language": meta.get("language"), "duration": meta["duration"],
               "words": [{"id": w["id"], "w": w["w"], "s": w["s"], "e": w["e"], "p": w.get("p", 1)} for w in words]},
              open(os.path.join(out, "transcript.json"), "w", encoding="utf-8"), indent=0)
    # readable: one line per phrase, each word tagged with its id, so plans can anchor to words
    lines, cur = [], []
    for w in words:
        if cur and (w["s"] - cur[-1]["e"] > 0.6 or len(cur) >= 14):
            lines.append(cur); cur = []
        cur.append(w)
    if cur: lines.append(cur)
    with open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8") as f:
        f.write("# [start-end] text   |   word ids (use {{at:wN}} tokens)\n")
        for ln in lines:
            f.write(f"[{ln[0]['s']:7.2f}-{ln[-1]['e']:7.2f}] " + " ".join(x["w"] for x in ln)
                    + f"   | {ln[0]['id']}..{ln[-1]['id']}\n")
    with open(os.path.join(out, "words.tsv"), "w", encoding="utf-8") as f:
        f.write("id\tstart\tend\tprob\tword\n")
        for w in words: f.write(f"{w['id']}\t{w['s']:.3f}\t{w['e']:.3f}\t{w.get('p', 1):.2f}\t{w['w']}\n")

def tonemap_chain(meta):
    if meta["transfer"] in ("arib-std-b67", "smpte2084") and "zscale" in run(["ffmpeg", "-hide_banner", "-filters"]):
        return ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
                "zscale=t=bt709:m=bt709:r=tv,")
    return ""

def make_proxy(video, meta, out, fps=30):
    """Edit-friendly copy: SDR, short side 1080, constant fps, a keyframe every second (HyperFrames
    seeks video frame by frame; sparse keyframes freeze on seek)."""
    vertical = meta["height"] >= meta["width"]
    scale = "scale=1080:-2" if vertical else "scale=-2:1080"
    vf = f"{tonemap_chain(meta)}{scale}:flags=lanczos,fps={fps},format=yuv420p"
    cmd = ["ffmpeg", "-y", "-i", video, "-vf", vf]
    if meta["has_audio"]: cmd += ["-map", "0:v:0", "-map", "0:a:0", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    else: cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v:0", "-map", "1:a", "-shortest", "-c:a", "aac"]
    run(cmd + ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-g", str(fps), "-keyint_min", str(fps),
               "-movflags", "+faststart", out])

def contact_sheet(video, out, n=30, width=200, cols=6, label=True, start=0.0, end=None):
    """Grid of frames with timestamps."""
    from PIL import Image, ImageDraw, ImageFont
    meta = probe(video)
    end = end or meta["duration"]
    tmp = out + "_frames"; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    times = [start + (end - start) * (i + 0.5) / n for i in range(n)]
    for i, t in enumerate(times):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                        "-vf", f"scale={width}:-2", os.path.join(tmp, f"{i:03d}.jpg")])
    ims = [(t, p) for t, p in zip(times, sorted(glob.glob(os.path.join(tmp, "*.jpg"))))]
    if not ims: return []
    first = Image.open(ims[0][1]); w, h = first.size
    rows = (len(ims) + cols - 1) // cols
    grid = Image.new("RGB", (cols * w, rows * h), (0, 0, 0)); d = ImageDraw.Draw(grid)
    try: fnt = ImageFont.truetype(font_path("mono"), 14)
    except Exception: fnt = ImageFont.load_default()
    for i, (t, p) in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * h
        grid.paste(Image.open(p).convert("RGB"), (x, y))
        if label:
            d.rectangle((x, y, x + 64, y + 20), fill=(0, 0, 0)); d.text((x + 4, y + 2), f"{t:5.1f}s", fill=(255, 255, 255), font=fnt)
    grid.save(out, quality=72)
    shutil.rmtree(tmp, ignore_errors=True)
    return times

def prepare(video, out, glossary=None, model=None, proxy=True):
    """Transcript + checks + frames (+ proxy). Writes into `out`."""
    os.makedirs(out, exist_ok=True)
    meta = probe(video)
    wav = os.path.join(out, "_audio.wav")
    extract_wav(video, wav)
    mean, peak = volume_stats(wav)
    words, model_name, lang = transcribe(wav, model, glossary)
    os.remove(wav)
    meta.update({"model": model_name, "language": lang})
    write_transcript(words, out, meta)
    warn = []
    if meta["width"] > meta["height"]: warn.append("Landscape source: design a vertical layout for it (zoom, split or framed).")
    if meta["transfer"] in ("arib-std-b67", "smpte2084"): warn.append("HDR (iPhone) source: converted to standard range.")
    if mean < -32: warn.append(f"Audio is quiet (mean {mean} dB): loudness is normalised, but background noise rises too.")
    if peak > -0.2: warn.append(f"Audio peaks at {peak} dB: possible clipping/distortion.")
    if meta["duration"] > 100: warn.append(f"Raw length {meta['duration']:.0f}s: tighten, or split into a 2-part series (sweet spot 35-90 s).")
    low = [w for w in words if w.get("p", 1) < 0.5]
    if low: warn.append(f"{len(low)} low-confidence words (check names/jargon): " + ", ".join(f"{w['w']}({w['id']})" for w in low[:30]))
    if not words: warn.append("No speech detected.")
    meta.update({"audio_mean_db": mean, "audio_peak_db": peak, "words": len(words), "warnings": warn})
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=2)
    contact_sheet(video, os.path.join(out, "frames.jpg"), n=min(36, max(12, int(meta["duration"] / 4))))
    if proxy:
        make_proxy(video, meta, os.path.join(out, "proxy.mp4"))
    return meta
