"""Wrapper around ci/jobs.py that adds background replacement, without editing jobs.py.

edit.json  "bg_remove": true   (or {"quality": "best"})
  After the engine builds a reel, cut Swati out of assets/base.mp4 with `hyperframes remove-background`
  -> assets/cutout.webm (alpha), so the composition can put a designed set behind her (index.html stacks
  base video for audio < #set < cutout). It is slow (~2 fps on CPU), so the cutout is cached on the release as
  cutout-<hash of base.mp4>.webm: a preview and the final with the same cuts reuse one cutout.
run.sh calls this file; everything else is jobs.py unchanged.
"""
import importlib.util, os, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("jobs", os.path.join(HERE, "jobs.py"))
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)

def bg_cutout(slug, b, opt):
    base = os.path.join(b, "assets", "base.mp4")
    dest = os.path.join(b, "assets", "cutout.webm")
    name = f"cutout-{J.fhash(base)}.webm"
    cache = os.path.join("_work", slug)
    if any(n == name for n, _ in J.release_assets(slug)):
        J.log(f"reusing {name} from the release")
        shutil.copy(J.download_asset(slug, name, cache), dest)
        return dest
    t0 = time.time()
    q = ["--quality", "best"] if isinstance(opt, dict) and opt.get("quality") == "best" else []
    J.sh(["hyperframes", "remove-background", base, "-o", dest, *q, "--json"], timeout=int(J.E("BG_TIMEOUT", "10800")))
    J.log(f"remove-background took {round(time.time() - t0)} s")
    os.makedirs(cache, exist_ok=True)
    shutil.copy(dest, os.path.join(cache, name))
    J.upload(slug, os.path.join(cache, name))
    return dest

_build = J.build
def build(slug, reel_dir=None, proxy=None):
    out, edit = _build(slug, reel_dir=reel_dir, proxy=proxy)
    if edit.get("bg_remove") and slug not in ("selftest", "gallery"):
        J.hf_install()
        bg_cutout(slug, out, edit.get("bg_remove"))
    return out, edit
J.build = build

def raw_asset(tag):
    vids = [(n, s) for n, s in J.release_assets(tag)
            if n.lower().endswith(J.VIDEO_EXT) and n not in J.GENERATED and not n.startswith("cutout-")]
    if not vids: raise RuntimeError(f"Release '{tag}' has no raw video attached. Attach the video to the release.")
    return max(vids, key=lambda x: x[1])[0]
J.raw_asset = raw_asset

if __name__ == "__main__":
    J.main()
