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
        B.main()
    else:
        import jobs
        variants.apply(jobs)
        import sfx
        sfx.main()
