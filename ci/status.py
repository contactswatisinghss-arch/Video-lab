"""Write reels/<slug>/status.json so Claude can read how a run went (it cannot see Actions logs).
usage: python ci/status.py <dir> <stage> <ok:true|false> <logfile> <run_url> [release_url]"""
import json, os, sys, time

d, stage, ok, log, url = sys.argv[1:6]
rel = sys.argv[6] if len(sys.argv) > 6 else ""
os.makedirs(d, exist_ok=True)
p = os.path.join(d, "status.json")
st = json.load(open(p)) if os.path.exists(p) else {"history": []}
tail = ""
if os.path.exists(log):
    lines = open(log, encoding="utf-8", errors="replace").read().splitlines()
    tail = "\n".join(lines[-40:])
entry = {"stage": stage, "ok": ok == "true", "time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
         "run": url, "release": rel, "log_tail": tail if ok != "true" else "\n".join(tail.splitlines()[-6:])}
for f in ("render_info.json",):
    fp = os.path.join("out", f)
    if stage == "render" and os.path.exists(fp): entry["render"] = json.load(open(fp))
st.update({"stage": stage, "ok": entry["ok"], "time": entry["time"], "run": url, "release": rel})
st["history"] = (st.get("history", []) + [entry])[-10:]
json.dump(st, open(p, "w"), indent=2)
print(json.dumps(entry, indent=2))
