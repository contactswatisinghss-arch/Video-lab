"""Wrapper around ci/jobs.py that adds background replacement, without editing jobs.py.

edit.json  "bg_remove": true   (or {"quality": "best"})
  After the engine builds a reel, cut Swati out of assets/base.mp4 with `hyperframes remove-background`
  -> assets/cutout.webm (alpha), so the composition can put a designed set behind her (index.html stacks
  base video for audio < #set < cutout). It is slow (~2 fps on CPU), so the cutout is cached on the release as
  cutout-<hash of base.mp4>.webm: a preview and the final with the same cuts reuse one cutout.
Also: every run catches up on published releases whose release-triggered run was dropped (see below), and
reels/<slug>/STILLS writes full-size frames for designing a cover (see bottom).
run.sh calls this file; everything else is jobs.py unchanged.
"""
import glob, importlib.util, json, os, shutil, sys, time, traceback

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

# ------------------------------------------------------------------ stills (for designing a cover)
# reels/<slug>/STILLS: times in seconds of the RAW video (as in frames.jpg), separated by spaces or newlines,
# "#" starts a comment. Writes full-size JPGs from the proxy (the same look as the Reel) to
# reels/<slug>/stills/NN.jpg, a 6-wide contact sheet stills/sheet.jpg and stills/done.json (index -> time).
# Runs again whenever STILLS changes. Quick (no render), and runs before any other pending job.
def stills_pending():
    out = []
    for p in sorted(glob.glob("reels/*/STILLS")):
        d = os.path.dirname(p)
        done = J.jload(os.path.join(d, "stills", "done.json"), {}) or {}
        if done.get("token") != J.fhash(p): out.append(os.path.basename(d))
    return out

def job_stills(slug):
    d = os.path.join("reels", slug); sd = os.path.join(d, "stills"); os.makedirs(sd, exist_ok=True)
    times = []
    for line in open(os.path.join(d, "STILLS"), encoding="utf-8"):
        for tok in line.split("#", 1)[0].replace(",", " ").split():
            try: times.append(float(tok))
            except ValueError: pass
    times = times[:48]
    info = {"token": J.fhash(os.path.join(d, "STILLS")), "time": J.NOW(), "run": J.E("RUN_URL"), "frames": {}}
    try:
        proxy = J.get_proxy(slug)
        for f in glob.glob(os.path.join(sd, "*.jpg")): os.remove(f)
        for i, t in enumerate(times):
            f = os.path.join(sd, f"{i:02d}.jpg")
            J.sh(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", proxy, "-frames:v", "1", "-q:v", "2", f])
            if os.path.exists(f): info["frames"][f"{i:02d}"] = t; J.changed_paths.add(f)
        if info["frames"]:
            sheet = os.path.join(sd, "sheet.jpg")
            n = len(times); rows = (n + 5) // 6
            J.sh(["ffmpeg", "-y", "-loglevel", "error", "-start_number", "0", "-i", os.path.join(sd, "%02d.jpg"),
                  "-vf", f"scale=270:480,drawtext=text='%{{frame_num}}':start_number=0:x=8:y=8:fontsize=34:fontcolor=white:box=1:boxcolor=black@0.7,tile=6x{rows}",
                  "-frames:v", "1", "-q:v", "3", sheet], check=False)
            if os.path.exists(sheet): J.changed_paths.add(sheet)
        info["ok"] = True
    except Exception as e:
        info.update({"ok": False, "error": f"{e}\n{J.log_tail(30)}"})
    J.jsave(os.path.join(sd, "done.json"), info)

_main = J.main
def main():
    todo = stills_pending()
    if todo:
        os.makedirs("_out", exist_ok=True)
        J.LOG = open("_out/log.txt", "a", encoding="utf-8")
        for slug in todo:
            J.log(f"\n======== stills {slug} ========")
            try: job_stills(slug)
            except Exception: J.log(traceback.format_exc())
            try: J.commit(f"reel-bot: stills {slug}"); J.changed_paths.clear()
            except Exception: J.log(traceback.format_exc())
    _main()
J.main = main

if __name__ == "__main__":
    main()
