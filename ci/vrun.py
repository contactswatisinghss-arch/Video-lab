"""Runs the Reels pipeline with the 12 Nov 2026 fixes switched on, without editing jobs.py/bgjobs.py/sfx.py.
  python ci/vrun.py bgjobs            run everything pending, one after another (old single-machine mode)
  python ci/vrun.py plan              print the parallel plan as JSON (used by ci/reels.yml)
  python ci/vrun.py one KIND TARGET   run ONE job (prepare|matte|preview|final|references|selftest) and commit
  python ci/vrun.py sfx               sound-effects variants (only reels that have sfx.json; off by default)
What it adds: variant reels (ci/variants.py), finals laid over the ORIGINAL upload (ci/overlay.py), one shared person
cutout per upload+cuts, live render progress in the log, parallel jobs, no re-preparing of deleted reels, PAUSE files.
"""
import importlib.util, json, os, subprocess, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import variants, overlay

def load():
    spec = importlib.util.spec_from_file_location("bgjobs", os.path.join(HERE, "bgjobs.py"))
    B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
    J = B.J
    variants.apply(J)

    # live output for long commands (renders, cutouts, FFmpeg) so progress is visible on GitHub
    def sh(cmd, cwd=None, check=True, timeout=None):
        J.log("$ " + (cmd if isinstance(cmd, str) else " ".join(map(str, cmd))))
        p = subprocess.Popen(cmd, cwd=cwd, shell=isinstance(cmd, str), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        out, t0 = [], time.time()
        for line in p.stdout:
            out.append(line); J.log("  " + line.rstrip())
            if timeout and time.time() - t0 > timeout:
                p.kill(); raise RuntimeError(f"timeout after {timeout}s: {str(cmd)[:200]}")
        rc = p.wait()
        if check and rc != 0:
            raise RuntimeError(f"exit {rc}: {(cmd if isinstance(cmd, str) else ' '.join(map(str, cmd)))[:300]}")
        return rc, "".join(out)
    J.sh = sh

    # one shared cutout per upload + cuts (stable key), used by previews, finals and every variant
    B.bg_cutout = lambda slug, b, opt: overlay.shared_cutout(J, slug, b, opt)

    # finals: overlay on the original upload unless the composition moves the camera or edit.json opts out
    J._job_final_rerender = J.job_final
    def job_final(slug):
        e = J.jload(os.path.join("reels", slug, "edit.json"), {}) or {}
        if (e.get("final") or {}).get("mode") == "rerender": return J._job_final_rerender(slug)
        return overlay.job_final_overlay(J, slug)
    J.job_final = job_final

    _pending = J.pending
    def pending():
        jobs = _pending()
        ev = os.environ.get("EVENT", "")
        ev_tag = os.environ.get("RELEASE_TAG", "") if ev == "release" else ""
        # a manual "Run workflow" with job=prepare and a target asks for that reel explicitly (e.g. a release
        # published before Actions was switched on), so it counts like the release event
        if ev == "workflow_dispatch" and os.environ.get("INPUT_JOB", "") == "prepare":
            ev_tag = os.environ.get("INPUT_TARGET", "")
        # never re-prepare old releases whose reel folder Swati deleted (catch-up only for brand-new uploads)
        jobs = [j for j in jobs if not (j[0] == "prepare" and len(j) > 1 and j[1] != ev_tag
                                        and not os.path.isdir(os.path.join("reels", j[1]))
                                        and not (J.jload(J.status_path(j[1]), {}) or {}))]
        # reels/<slug>/PAUSE: skip that reel's preview/final until the file is removed
        jobs = [j for j in jobs if not (j[0] in ("preview", "final") and len(j) > 1
                                        and os.path.exists(os.path.join("reels", j[1], "PAUSE")))]
        return jobs
    J.pending = pending
    return B, J

def needs_matte(J, j):
    if j[0] not in ("preview", "final") or len(j) < 2: return None
    e = J.jload(os.path.join("reels", j[1], "edit.json"), {}) or {}
    if not e.get("bg_remove"): return None
    try: key = overlay.matte_key(J, j[1])
    except Exception: return None
    return key

def plan(J):
    """Parallel plan: prepares + quick jobs start at once; each distinct cutout is made ONCE (matte job) and every
    preview/final that needs it waits for it, so two versions never redo the same work."""
    jobs = J.pending()
    fast, slow, mattes = [], [], {}
    for j in jobs:
        key = needs_matte(J, j)
        item = {"kind": j[0], "target": j[1] if len(j) > 1 else ""}
        if key:
            mattes.setdefault(key, j[1]); slow.append(item)
        else:
            fast.append(item)
    cached = set()
    for key, slug in mattes.items():
        try:
            if any(n == key for n, _ in J.release_assets(slug)): cached.add(key)
        except Exception: pass
    matte_jobs = [{"kind": "matte", "target": slug} for key, slug in mattes.items() if key not in cached]
    if matte_jobs:   # the cutout run needs the slow jobs after it; nothing else waits
        pass
    else:
        fast += slow; slow = []
    return {"fast": fast, "matte": matte_jobs, "slow": slow}

def job_matte(J, B, slug):
    J.hf_install()
    proxy = J.get_proxy(slug)
    b = os.path.abspath(os.path.join("_build", slug + "_matte"))
    J.sh([sys.executable, "-m", "engine", "build", "--reel", os.path.join("reels", slug), "--out", b, "--proxy", proxy], timeout=3600)
    edit = J.jload(os.path.join("reels", slug, "edit.json"), {}) or {}
    overlay.shared_cutout(J, slug, b, edit.get("bg_remove"))

def one(B, J, kind, target):
    os.makedirs("_out", exist_ok=True)
    J.LOG = open("_out/log.txt", "a", encoding="utf-8")
    J.log(f"\n======== {kind} {target} ========")
    if kind not in ("matte",) and not any(j[0] == kind and (len(j) < 2 or j[1] == target) for j in J.pending()):
        J.log("already done by another run; nothing to do"); return
    J.heartbeat("running", [f"{kind} {target}"], f"{kind} {target}")
    try:
        if kind == "prepare": J.job_prepare(target)
        elif kind == "matte": job_matte(J, B, target)
        elif kind == "preview": J.job_preview(target)
        elif kind == "final": J.job_final(target)
        elif kind == "references":
            url = dict(J.queue()).get(target, "")
            if url.startswith("search:"): J.job_search(target, url[7:])
            else: J.job_reference(target, url=url)
        elif kind == "ref_release": J.job_reference(target, tag=f"ref-{target}")
        elif kind == "selftest": J.job_selftest()
    except Exception:
        J.log(traceback.format_exc())
    J.commit(f"reel-bot: {kind} {target}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "bgjobs"
    if target == "sfx":
        import jobs
        variants.apply(jobs)
        import sfx
        sfx.main()
    else:
        B, J = load()
        if target == "plan":
            print(json.dumps(plan(J)))
        elif target == "one":
            one(B, J, sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
        else:
            # single machine: cutout jobs last so quick jobs are never stuck behind them
            _p = J.pending
            def ordered():
                jobs = _p()
                return [j for j in jobs if not needs_matte(J, j)] + [j for j in jobs if needs_matte(J, j)]
            J.pending = ordered
            B.main()
