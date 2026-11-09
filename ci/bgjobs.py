"""Wrapper around ci/jobs.py that adds background replacement, without editing jobs.py.

edit.json  "bg_remove": true   (or {"quality": "best"})
  After the engine builds a reel, cut Swati out of assets/base.mp4 with `hyperframes remove-background`
  -> assets/cutout.webm (alpha), so the composition can put a designed set behind her (index.html stacks
  base video for audio < #set < cutout). It is slow (~2 fps on CPU), so the cutout is cached on the release as
  cutout-<hash of base.mp4>.webm: a preview and the final with the same cuts reuse one cutout.
Also: every run catches up on published releases whose release-triggered run was dropped (see bottom).
run.sh calls this file; everything else is jobs.py unchanged.
"""
import importlib.util, json, os, shutil, sys, time

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

# ------------------------------------------------------------------ catch up on dropped releases
# GitHub keeps only ONE waiting run per concurrency group, so when several videos are uploaded close
# together, some release-triggered runs are silently dropped. Every run now also prepares any published
# reel release that has no transcript and no prepare attempt yet. (A failed prepare re-runs via PREPARE.)
def unprepared_releases():
    try:
        rc, out = J.sh(["gh", "release", "list", "--limit", "50", "--exclude-drafts", "--json", "tagName"], check=False, timeout=120)
        if rc != 0: return []
        tags = [r["tagName"] for r in json.loads(out)]
    except Exception as e:
        J.log(f"release catch-up skipped: {e}"); return []
    todo = []
    for tag in tags:
        if not tag or tag.startswith("ref-") or "/" in tag: continue
        if os.path.exists(os.path.join("reels", tag, "transcript.json")): continue
        if "prepare" in (J.jload(J.status_path(tag), {}) or {}): continue
        todo.append(tag)
    return todo

_pending = J.pending
def pending():
    jobs = _pending()
    if J.E("EVENT", "") == "workflow_dispatch" and J.E("INPUT_JOB", "all") not in ("", "all"):
        return jobs
    preps = [j for j in jobs if j[0] == "prepare"]
    preps += [("prepare", t) for t in unprepared_releases() if ("prepare", t) not in preps]
    # prepares first: they are quicker than renders and unblock storyboarding of new videos
    return preps + [j for j in jobs if j[0] != "prepare"]
J.pending = pending

if __name__ == "__main__":
    J.main()
