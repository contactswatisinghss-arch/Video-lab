"""Sound-effects variant (Swati, Nov 2026: "always give me both, so I just pick").

For every reel with reels/<slug>/sfx.json, after the normal jobs:
  preview ok  -> preview_sfx.mp4    (same picture, original sound effects mixed under her voice)
  final ok    -> final_reel_sfx.mp4
The clean files (preview.mp4, final_reel.mp4) are never touched.

reels/<slug>/sfx.json (kept outside hf/ so it never forces a re-render) uses the same time tokens as the composition, e.g.
  {"cues": [["whoosh", {{at:w52}}], ["hit", {{at:w129}}], ["riser", {{at:w166}}, {{at:w169}}], ["drone", {{at:w92}}, {{at:w104}}]]}
Kinds: whoosh, hit, pop, tick, shimmer, glitch, riser (start, end), drone (start, end); optional 3rd/4th item = gain dB offset.
Everything is synthesised here (no downloaded audio), kept ~20 dB under the voice and ducked further while she speaks.
"""
import json, os, subprocess, sys, wave
import numpy as np

SR = 48000
BASE_DB = {"whoosh": -25, "hit": -23, "pop": -29, "tick": -33, "shimmer": -31, "glitch": -27, "riser": -27, "drone": -40}

def _db(x): return 10 ** (x / 20.0)

def _band_noise(n, lo, hi, seed):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    f = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1 / SR)
    f[(fr < lo) | (fr > hi)] = 0
    y = np.fft.irfft(f, n)
    return y / (np.max(np.abs(y)) + 1e-9)

def _env(n, attack_frac):
    a = max(1, int(n * attack_frac))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a) ** 2
    e[a:] = np.linspace(1, 0, n - a) ** 2
    return e

def synth(kind, dur_hint=None, seed=0):
    if kind == "whoosh":
        n = int(0.42 * SR)
        lo = _band_noise(n, 300, 1500, seed); hi = _band_noise(n, 1500, 6000, seed + 1)
        sweep = np.linspace(0, 1, n)
        y = (lo * (1 - sweep) + hi * sweep) * _env(n, 0.55)
        return y, 0.55 * 0.42          # peak lands on the cue
    if kind == "hit":
        n = int(0.45 * SR); t = np.arange(n) / SR
        y = 0.8 * np.sin(2 * np.pi * 58 * t) * np.exp(-t / 0.12) + 0.35 * np.sin(2 * np.pi * 116 * t) * np.exp(-t / 0.07)
        y[: int(0.004 * SR)] += _band_noise(int(0.004 * SR), 1000, 8000, seed) * 0.4
        return y, 0.0
    if kind == "pop":
        n = int(0.09 * SR); t = np.arange(n) / SR
        f = np.linspace(700, 1250, n)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.025)
        return y, 0.0
    if kind == "tick":
        n = int(0.02 * SR); t = np.arange(n) / SR
        return np.sin(2 * np.pi * 2200 * t) * np.exp(-t / 0.004), 0.0
    if kind == "shimmer":
        n = int(1.0 * SR); t = np.arange(n) / SR
        y = sum(np.sin(2 * np.pi * f * t) for f in (1046.5, 1318.5, 1568.0, 2093.0)) / 4
        return y * np.exp(-t / 0.35) * np.minimum(1, t / 0.01), 0.0
    if kind == "glitch":
        n = int(0.32 * SR); y = np.zeros(n)
        for i, s in enumerate((0.0, 0.07, 0.15, 0.24)):
            a, m = int(s * SR), int(0.035 * SR)
            tt = np.arange(m) / SR
            y[a:a + m] += np.sign(np.sin(2 * np.pi * (170 + 40 * i) * tt)) * 0.5 + _band_noise(m, 800, 5000, seed + i) * 0.5
        return y, 0.0
    if kind == "riser":
        d = max(0.3, dur_hint or 1.0); n = int(d * SR); t = np.arange(n) / SR
        f = 180 + (1100 - 180) * (t / d) ** 2
        tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
        y = (0.6 * tone + 0.5 * _band_noise(n, 2000, 9000, seed)) * (t / d) ** 2
        y[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
        return y, 0.0
    if kind == "drone":
        d = max(0.5, dur_hint or 2.0); n = int(d * SR); t = np.arange(n) / SR
        y = (np.sin(2 * np.pi * 55 * t) + 0.6 * np.sin(2 * np.pi * 82.4 * t) + 0.4 * np.sin(2 * np.pi * 110 * t)) / 2
        fade = np.minimum(1, np.minimum(t / 0.6, (d - t) / 0.6))
        return y * np.clip(fade, 0, 1), 0.0
    raise ValueError(f"unknown sfx kind {kind}")

def render_track(cues, duration, out_wav):
    n = int((duration + 1) * SR); mix = np.zeros(n)
    for i, c in enumerate(cues):
        kind, t0 = c[0], float(c[1])
        span = kind in ("riser", "drone")
        t1 = float(c[2]) if span and len(c) > 2 else None
        gain = c[3] if span and len(c) > 3 else (c[2] if not span and len(c) > 2 else 0)
        y, lead = synth(kind, (t1 - t0) if t1 else None, seed=i)
        y = y / (np.max(np.abs(y)) + 1e-9) * _db(BASE_DB[kind] + float(gain))
        a = int((t0 - lead) * SR)
        if a < 0: y, a = y[-a:], 0
        b = min(n, a + len(y)); mix[a:b] += y[: b - a]
    mix = np.clip(mix, -0.5, 0.5)
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def mix_into(video, sfx_wav, out):
    """SFX ducked ~8 dB while she speaks (sidechain on her voice), then added under it. Picture copied as is."""
    fc = ("[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[v][k];[1:a]aresample=48000,aformat=channel_layouts=stereo[s];"
          "[s][k]sidechaincompress=threshold=0.03:ratio=6:attack=8:release=280[d];"
          "[v][d]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[a]")
    subprocess.run(["ffmpeg", "-y", "-i", video, "-i", sfx_wav, "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], check=True, capture_output=True)

def resolve_cues(reel_dir):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from engine.edit import Timeline, load_edit, resolve
    tl = Timeline(os.path.join(reel_dir, "transcript.json"), load_edit(reel_dir))
    txt = resolve(open(os.path.join(reel_dir, "sfx.json"), encoding="utf-8").read(), tl, where="sfx.json")
    return json.loads(txt)["cues"], tl.duration

def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import glob, jobs
    for d in sorted(glob.glob("reels/*/sfx.json")):
        reel = os.path.dirname(d); slug = os.path.basename(reel)
        st = jobs.jload(jobs.status_path(slug), {}) or {}
        sx = st.get("sfx") or {}
        sfx_hash = jobs.fhash(d)
        todo = []
        for stage, src, dst in (("preview", "preview.mp4", "preview_sfx.mp4"), ("final", "final_reel.mp4", "final_reel_sfx.mp4")):
            s = st.get(stage) or {}
            if s.get("ok") and s.get("hash") and (sx.get(stage + "_hash") != s["hash"] or sx.get("cues_hash") != sfx_hash or not sx.get(stage + "_ok")):
                todo.append((stage, src, dst, s["hash"]))
        if not todo: continue
        try:
            cues, dur = resolve_cues(reel)
            work = os.path.join("_work", slug, "sfx"); os.makedirs(work, exist_ok=True)
            wav = os.path.join(work, "sfx.wav"); render_track(cues, dur, wav)
            for stage, src, dst, h in todo:
                v = jobs.download_asset(slug, src, work)
                out = os.path.join(work, dst); mix_into(v, wav, out); jobs.upload(slug, out)
                sx.update({stage + "_hash": h, stage + "_ok": True, stage + "_video": f"{jobs.E('REPO_URL')}/releases/download/{slug}/{dst}"})
            sx.update({"cues_hash": sfx_hash, "cues": len(cues), "time": jobs.NOW(), "error": None})
        except Exception as e:
            sx.update({"error": str(e)[-1500:], "time": jobs.NOW()})
            for stage, *_ in todo: sx[stage + "_ok"] = False
        st["sfx"] = sx; jobs.jsave(jobs.status_path(slug), st)
        jobs.commit(f"reel-bot: sfx {slug}")

if __name__ == "__main__":
    main()
