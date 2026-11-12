"""Runs ci/bgjobs.py or ci/sfx.py with variant support (ci/variants.py) switched on, without editing them.
  python ci/vrun.py bgjobs     (instead of python ci/bgjobs.py)
  python ci/vrun.py sfx        (instead of python ci/sfx.py)
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import variants

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "bgjobs"
    if target == "bgjobs":
        spec = importlib.util.spec_from_file_location("bgjobs", os.path.join(HERE, "bgjobs.py"))
        B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
        variants.apply(B.J)
        # previews/finals that need a background cutout are slow (~40 min): run every other job first
        _pending = B.J.pending
        def pending():
            jobs = _pending()
            def slow(j):
                if j[0] not in ("preview", "final") or len(j) < 2: return False
                try:
                    import json as _j
                    return bool((_j.load(open(os.path.join("reels", j[1], "edit.json"), encoding="utf-8")) or {}).get("bg_remove"))
                except Exception: return False
            # never re-prepare old releases whose reel folder Swati deleted (catch-up only for brand-new uploads)
            ev_tag = os.environ.get("RELEASE_TAG", "") if os.environ.get("EVENT", "") == "release" else ""
            jobs = [j for j in jobs if not (j[0] == "prepare" and len(j) > 1 and j[1] != ev_tag
                                            and not os.path.isdir(os.path.join("reels", j[1])))]
            # reels/<slug>/PAUSE: skip that reel's preview/final until the file is removed (Swati can pause work)
            jobs = [j for j in jobs if not (j[0] in ("preview", "final") and len(j) > 1 and os.path.exists(os.path.join("reels", j[1], "PAUSE")))]
            return [j for j in jobs if not slow(j)] + [j for j in jobs if slow(j)]
        B.J.pending = pending
        B.main()
    else:
        import jobs
        variants.apply(jobs)
        import sfx
        sfx.main()
