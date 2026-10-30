"""Reel engine v2 CLI.

  python3 -m engine prepare  --video raw.mp4 --out reels/<slug> [--glossary reels/glossary.txt] [--no-proxy]
  python3 -m engine timeline --reel reels/<slug>                      # final timeline from edit.json (no video)
  python3 -m engine build    --reel reels/<slug> --out _build/<slug> [--proxy proxy.mp4]   # resolved HF project (+ base.mp4)
  python3 -m engine preview  --reel reels/<slug> --times 0.5,3,8 --out sheet.jpg            # local stand-in preview
  python3 -m engine refs     --video ref.mp4 --out references/<name> [--url URL]
  python3 -m engine finish   --video render.mp4 --base base.mp4 --out final_reel.mp4         # audio safety + loudness
"""
import argparse, json, os, sys
from .util import ReelError, run

def main(argv=None):
    ap = argparse.ArgumentParser(prog="engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--video", required=True); p.add_argument("--out", required=True)
    p.add_argument("--glossary"); p.add_argument("--model"); p.add_argument("--no-proxy", action="store_true")
    t = sub.add_parser("timeline"); t.add_argument("--reel", required=True)
    b = sub.add_parser("build"); b.add_argument("--reel", required=True); b.add_argument("--out", required=True)
    b.add_argument("--proxy")
    v = sub.add_parser("preview"); v.add_argument("--reel", required=True); v.add_argument("--out", required=True)
    v.add_argument("--times", required=True); v.add_argument("--build", default=None)
    r = sub.add_parser("refs"); r.add_argument("--video", required=True); r.add_argument("--out", required=True); r.add_argument("--url")
    f = sub.add_parser("finish"); f.add_argument("--video", required=True); f.add_argument("--base", required=True)
    f.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "prepare":
        from .media import prepare
        m = prepare(a.video, a.out, a.glossary, a.model, proxy=not a.no_proxy)
        print(json.dumps({"words": m["words"], "duration": m["duration"], "warnings": m["warnings"]}, indent=1))
    elif a.cmd == "timeline":
        from .edit import Timeline, load_edit
        tl = Timeline(os.path.join(a.reel, "transcript.json"), load_edit(a.reel))
        json.dump(tl.to_json(), open(os.path.join(a.reel, "timeline.json"), "w"), indent=1)
        print(f"final {tl.duration}s (raw {tl.raw_duration:.1f}s, {len(tl.keeps)} segments, {len(tl.words)} words)")
    elif a.cmd == "build":
        from .edit import build_project, build_base, load_edit
        from .fonts import install_fonts
        edit = load_edit(a.reel)
        os.makedirs(os.path.join(a.out, "assets"), exist_ok=True)
        ff = install_fonts(edit.get("fonts", []), os.path.join(a.out, "assets"))
        tl, warn = build_project(a.reel, a.out, fontfaces=ff)
        if a.proxy:
            build_base(a.proxy, tl, os.path.join(a.out, "assets", "base.mp4"), edit.get("audio", {}).get("loudnorm", True))
        print(json.dumps({"duration": tl.duration, "warnings": warn}))
    elif a.cmd == "preview":
        from .preview import snapshot
        res = snapshot(a.reel, a.build or os.path.join("_build", os.path.basename(os.path.normpath(a.reel))),
                       [float(x) for x in a.times.split(",")], a.out)
        print(json.dumps({k: res[k] for k in ("duration", "errors", "warnings", "comps")}, indent=1))
    elif a.cmd == "refs":
        from .refs import analyse
        print(json.dumps(analyse(a.video, a.out, a.url), indent=1))
    elif a.cmd == "finish":
        from .media import probe
        meta = probe(a.video)
        if meta["has_audio"]:
            run(["ffmpeg", "-y", "-i", a.video, "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
                 "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-c:a", "aac", "-b:a", "192k",
                 "-movflags", "+faststart", a.out])
        else:   # composition had no audio: take the base video's
            run(["ffmpeg", "-y", "-i", a.video, "-i", a.base, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                 "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out])
        print(a.out)

if __name__ == "__main__":
    try: main()
    except ReelError as e:
        print("\nERROR:", e, file=sys.stderr); sys.exit(1)
