"""Works out what is pending and does it. State lives in the repo, so every run catches up on all
pending work even if GitHub skipped a queued run.

Jobs
  prepare     release published (tag = reel slug) or reels/<slug>/PREPARE changed
              -> transcript.json/.txt, words.tsv, meta.json, frames.jpg; proxy.mp4 attached to the release
  preview     reels/<slug>/{edit.json, hf/**} changed since the last preview
              -> HyperFrames check + review sheets + draft render (preview.mp4 on the release)
  final       reels/<slug>/RENDER created/changed (the approval)  -> final_reel.mp4, cover.jpg, caption.txt on the release
  references  references/queue.txt has a name without analysis, or a release tagged ref-<name>
  selftest    selftest/run.txt changed  -> selftest/out/result.json
Each job writes a status.json (ok, log tail, links) so Claude can follow along without Actions logs.
"""
import glob, hashlib, json, os, re, shutil, subprocess, sys, time, traceback

E = os.environ.get
NOW = lambda: time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".mkv", ".webm")
GENERATED = ("proxy.mp4", "preview.mp4", "final_reel.mp4")
LOG = None
changed_paths = set()

def log(msg):
    print(msg, flush=True)
    if LOG: LOG.write(msg + "\n"); LOG.flush()

def sh(cmd, cwd=None, check=True, timeout=None):
    log("$ " + (cmd if isinstance(cmd, str) else " ".join(map(str, cmd))))
    p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines()[-400:]: log("  " + line)
    if check and p.returncode != 0:
        raise RuntimeError(f"exit {p.returncode}: {(cmd if isinstance(cmd, str) else ' '.join(map(str, cmd)))[:300]}")
    return p.returncode, p.stdout or ""

def jload(p, default=None):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return default

def jsave(p, obj):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    changed_paths.add(p)

def fhash(*paths):
    h = hashlib.sha256()
    for p in paths:
        if os.path.isdir(p):
            for f in sorted(glob.glob(os.path.join(p, "**", "*"), recursive=True)):
                if os.path.isfile(f): h.update(f.encode()); h.update(open(f, "rb").read())
        elif os.path.exists(p):
            h.update(p.encode()); h.update(open(p, "rb").read())
    return h.hexdigest()[:16]

# ------------------------------------------------------------------ GitHub release helpers
def release_assets(tag):
    rc, out = sh(["gh", "release", "view", tag, "--json", "assets"], check=False)
    if rc != 0: return []
    return [(a["name"], a.get("size", 0)) for a in json.loads(out).get("assets", [])]

def download_asset(tag, name, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    sh(["gh", "release", "download", tag, "-p", name, "-D", dest_dir, "--clobber"])
    return os.path.join(dest_dir, name)

def raw_asset(tag):
    vids = [(n, s) for n, s in release_assets(tag) if n.lower().endswith(VIDEO_EXT) and n not in GENERATED]
    if not vids: raise RuntimeError(f"Release '{tag}' has no raw video attached. Attach the video to the release.")
    return max(vids, key=lambda x: x[1])[0]

def upload(tag, *files):
    sh(["gh", "release", "upload", tag, *files, "--clobber"])

# ------------------------------------------------------------------ status
def status_path(slug): return os.path.join("reels", slug, "status.json")

def set_status(slug, stage, ok, extra=None, err=None):
    p = status_path(slug)
    st = jload(p, {}) or {}
    entry = {"stage": stage, "ok": ok, "time": NOW(), "run": E("RUN_URL"), **(extra or {})}
    if err: entry["error"] = err[-1500:]
    st.update({"slug": slug, "stage": stage, "ok": ok, "time": entry["time"], "run": E("RUN_URL"),
               "release": f"{E('REPO_URL')}/releases/tag/{slug}"})
    st[stage] = entry
    st["history"] = (st.get("history", []) + [{k: entry[k] for k in ("stage", "ok", "time")}])[-12:]
    jsave(p, st)
    return st

def log_tail(n=60):
    if not LOG: return ""
    LOG.flush()
    lines = open(LOG.name, encoding="utf-8", errors="replace").read().splitlines()
    return "\n".join(lines[-n:])

# ------------------------------------------------------------------ HyperFrames
HF = {"ready": False, "version": None}

def hf_install():
    if HF["ready"]: return
    ver = E("HF_VERSION", "latest")
    sh(["npm", "install", "-g", f"hyperframes@{ver}"], timeout=900)
    rc, out = sh(["hyperframes", "--version"], check=False)
    HF["version"] = out.strip().splitlines()[-1] if out.strip() else ver
    sh(["hyperframes", "browser", "ensure"], check=False, timeout=900)
    HF["ready"] = True

def summarize_check(raw):
    try: j = json.loads(raw[raw.index("{"):])
    except Exception: return {"parsed": False, "raw_tail": raw[-3000:]}
    findings = []
    def walk(x, section=""):
        if isinstance(x, dict):
            if "code" in x and isinstance(x.get("code"), str):
                findings.append({k: x.get(k) for k in ("severity", "level", "code", "message", "selector", "time", "file", "fix") if x.get(k) is not None} | {"section": section})
            for k, v in x.items(): walk(v, k if isinstance(v, (list, dict)) else section)
        elif isinstance(x, list):
            for v in x: walk(v, section)
    walk(j)
    sev = lambda f: str(f.get("severity") or f.get("level") or "").lower()
    errors = [f for f in findings if sev(f) in ("error", "fatal")]
    warns = [f for f in findings if sev(f) in ("warning", "warn")]
    return {"parsed": True, "ok": j.get("ok"), "errors": len(errors), "warnings": len(warns),
            "top_errors": errors[:25], "top_warnings": warns[:25]}

def hf_check_snap_render(build, out_dir, quality):
    """check -> review sheets -> render. Returns (summary dict, rendered path)."""
    os.makedirs(out_dir, exist_ok=True)
    rc, out = sh("hyperframes check --json", cwd=build, check=False, timeout=900)
    open(os.path.join(out_dir, "check.json"), "w").write(out[:400000])
    summary = {"check": summarize_check(out), "hf_version": HF["version"]}
    snaps = os.path.join(out_dir, "snaps")
    rc2, out2 = sh(f"hyperframes snapshot --review --json --output {os.path.abspath(snaps)}", cwd=build, check=False, timeout=900)
    summary["snapshot_ok"] = rc2 == 0
    t0 = time.time()
    render = os.path.join(out_dir, "render.mp4")
    sh(f"hyperframes render --quality {quality} --fps 30 --output {os.path.abspath(render)}", cwd=build, timeout=7200)
    summary["render_seconds"] = round(time.time() - t0)
    return summary, render

def hf_add(build, names):
    for n in names or []:
        sh(f"hyperframes add {n} --json", cwd=build, check=False, timeout=300)

# ------------------------------------------------------------------ jobs
def job_prepare(slug):
    d = os.path.join("reels", slug); os.makedirs(d, exist_ok=True)
    try:
        name = raw_asset(slug)
        raw = download_asset(slug, name, os.path.join("in", slug))
        gl = ["--glossary", "reels/glossary.txt"] if os.path.exists("reels/glossary.txt") else []
        sh([sys.executable, "-m", "engine", "prepare", "--video", raw, "--out", d, *gl, "--model", E("WHISPER_MODEL", "medium.en")], timeout=5400)
        proxy = os.path.join(d, "proxy.mp4")
        work = os.path.join("_work", slug); os.makedirs(work, exist_ok=True)
        shutil.move(proxy, os.path.join(work, "proxy.mp4"))
        upload(slug, os.path.join(work, "proxy.mp4"))
        for f in ("transcript.json", "transcript.txt", "words.tsv", "meta.json", "frames.jpg"): changed_paths.add(os.path.join(d, f))
        meta = jload(os.path.join(d, "meta.json"), {})
        tok = open(os.path.join(d, "PREPARE")).read() if os.path.exists(os.path.join(d, "PREPARE")) else ""
        st = set_status(slug, "prepare", True, {"raw": name, "words": meta.get("words"), "duration": meta.get("duration"),
                                                  "warnings": meta.get("warnings", []), "token": fhash(os.path.join(d, "PREPARE")) if tok else ""})
    except Exception as e:
        set_status(slug, "prepare", False, err=f"{e}\n{log_tail()}")

def get_proxy(slug):
    p = os.path.join("_work", slug, "proxy.mp4")
    if os.path.exists(p): return p
    if any(n == "proxy.mp4" for n, _ in release_assets(slug)):
        return download_asset(slug, "proxy.mp4", os.path.join("_work", slug))
    # older release without a proxy: make one
    from engine.media import probe, make_proxy
    raw = download_asset(slug, raw_asset(slug), os.path.join("in", slug))
    make_proxy(raw, probe(raw), p); upload(slug, p)
    return p

def build(slug, reel_dir=None, proxy=None):
    reel_dir = reel_dir or os.path.join("reels", slug)
    out = os.path.abspath(os.path.join("_build", slug))
    sh([sys.executable, "-m", "engine", "build", "--reel", reel_dir, "--out", out] + (["--proxy", proxy] if proxy else []), timeout=3600)
    edit = jload(os.path.join(reel_dir, "edit.json"), {})
    hf_add(out, edit.get("hf_add"))
    if os.path.exists(os.path.join(reel_dir, "timeline.json")): changed_paths.add(os.path.join(reel_dir, "timeline.json"))
    return out, edit

def job_preview(slug):
    d = os.path.join("reels", slug); h = fhash(os.path.join(d, "edit.json"), os.path.join(d, "transcript.json"), os.path.join(d, "hf"))
    try:
        hf_install()
        proxy = get_proxy(slug)
        b, edit = build(slug, proxy=proxy)
        out = os.path.join("_out", slug)
        summary, render = hf_check_snap_render(b, out, "draft")
        full = os.path.join(out, "preview_full.mp4")
        sh([sys.executable, "-m", "engine", "finish", "--video", render, "--base", os.path.join(b, "assets", "base.mp4"), "--out", full])
        small = os.path.join(out, "preview.mp4")
        sh(["ffmpeg", "-y", "-i", full, "-vf", "scale=540:-2", "-c:v", "libx264", "-crf", "28", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", small])
        upload(slug, small)
        pv = os.path.join(d, "preview"); os.makedirs(pv, exist_ok=True)
        from engine.media import contact_sheet
        contact_sheet(full, os.path.join(pv, "sheet.jpg"), n=16, width=270, cols=4); changed_paths.add(os.path.join(pv, "sheet.jpg"))
        for f in ("review-beats.jpg", "review-phone.jpg"):
            src = glob.glob(os.path.join(out, "snaps", "**", f), recursive=True)
            if src: shutil.copy(src[0], os.path.join(pv, f)); changed_paths.add(os.path.join(pv, f))
        shutil.copy(os.path.join(out, "check.json"), os.path.join(pv, "check.json")); changed_paths.add(os.path.join(pv, "check.json"))
        set_status(slug, "preview", True, {"hash": h, **summary, "video": f"{E('REPO_URL')}/releases/download/{slug}/preview.mp4"})
    except Exception as e:
        set_status(slug, "preview", False, {"hash": h}, err=f"{e}\n{log_tail()}")

def job_final(slug):
    d = os.path.join("reels", slug)
    h = fhash(os.path.join(d, "RENDER"), os.path.join(d, "edit.json"), os.path.join(d, "transcript.json"), os.path.join(d, "hf"))
    try:
        hf_install()
        proxy = get_proxy(slug)
        b, edit = build(slug, proxy=proxy)
        out = os.path.join("_out", slug)
        summary, render = hf_check_snap_render(b, out, "delivery")
        final = os.path.join(out, "final_reel.mp4")
        sh([sys.executable, "-m", "engine", "finish", "--video", render, "--base", os.path.join(b, "assets", "base.mp4"), "--out", final])
        cover = os.path.join(out, "cover.jpg")
        sh(["ffmpeg", "-y", "-ss", f"{float(edit.get('cover_at', 1.0)):.2f}", "-i", final, "-frames:v", "1", "-q:v", "2", cover])
        files = [final, cover]
        post = edit.get("post") or {}
        if post:
            cap = os.path.join(out, "caption.txt")
            open(cap, "w", encoding="utf-8").write((post.get("caption", "").strip() + "\n\n" + " ".join(post.get("hashtags", []))).strip() + "\n")
            files.append(cap)
        upload(slug, *files)
        rv = os.path.join(d, "review"); os.makedirs(rv, exist_ok=True)
        from engine.media import contact_sheet, probe
        contact_sheet(final, os.path.join(rv, "sheet.jpg"), n=16, width=270, cols=4)
        shutil.copy(cover, os.path.join(rv, "cover.jpg"))
        for f in ("sheet.jpg", "cover.jpg"): changed_paths.add(os.path.join(rv, f))
        m = probe(final)
        set_status(slug, "final", True, {"hash": h, **summary, "seconds": round(m["duration"], 2), "size_mb": m["size_mb"],
                                         "video": f"{E('REPO_URL')}/releases/download/{slug}/final_reel.mp4"})
        set_status(slug, "preview", True, {"hash": fhash(os.path.join(d, "edit.json"), os.path.join(d, "transcript.json"), os.path.join(d, "hf")), "note": "covered by final render"})
    except Exception as e:
        set_status(slug, "final", False, {"hash": h}, err=f"{e}\n{log_tail()}")

def ytdlp_args():
    args = ["yt-dlp", "--no-playlist", "--no-warnings"]
    if E("YTDLP_COOKIES"):
        ck = os.path.abspath("_work/cookies.txt"); os.makedirs("_work", exist_ok=True)
        open(ck, "w").write(E("YTDLP_COOKIES")); args += ["--cookies", ck]
    return args

def ytdlp_download(url, dest_dir):
    """Video + its info JSON (views, likes, comments, followers)."""
    os.makedirs(dest_dir, exist_ok=True)
    sh(ytdlp_args() + ["--max-filesize", "600M", "-f", "bv*[height<=1920]+ba/b", "--merge-output-format", "mp4",
                       "--write-info-json", "-o", os.path.join(dest_dir, "ref.%(ext)s"), url], timeout=900)
    vids = [p for p in glob.glob(os.path.join(dest_dir, "ref.*")) if p.lower().endswith(VIDEO_EXT)]
    if not vids: raise RuntimeError("yt-dlp finished but no video file was written")
    info = jload(os.path.join(dest_dir, "ref.info.json"), {}) or {}
    return vids[0], info

def job_reference(name, url=None, tag=None):
    d = os.path.join("references", name)
    try:
        info = {}
        if url: video, info = ytdlp_download(url, os.path.join("in", "ref", name))
        else: video = download_asset(tag, raw_asset(tag), os.path.join("in", "ref", name))
        from engine.refs import analyse
        analyse(video, d, url=url, model=E("REF_WHISPER_MODEL", "small.en"), info=info)
        for f in ("analysis.json", "transcript.txt", "hook.jpg", "frames.jpg"): changed_paths.add(os.path.join(d, f))
        jsave(os.path.join(d, "status.json"), {"ok": True, "time": NOW(), "source": url or f"release {tag}", "run": E("RUN_URL")})
    except Exception as e:
        jsave(os.path.join(d, "status.json"), {"ok": False, "time": NOW(), "source": url or f"release {tag}", "run": E("RUN_URL"),
                                                "error": f"{e}\n{log_tail(40)}",
                                                "fallback": f"Create a release tagged ref-{name} with the video attached."})

def job_search(name, query, top=3, n=15, max_len=95):
    """Find what's working: search short videos on a topic, rank by views and engagement, analyse the top ones.
    YouTube Shorts is searchable from GitHub; Instagram has no public search, so Instagram Reels come in as URLs."""
    d = os.path.join("references", name)
    try:
        rc, out = sh(ytdlp_args() + ["--skip-download", "--dump-json", f"ytsearch{n}:{query} #shorts"], check=False, timeout=1200)
        items = []
        for line in out.splitlines():
            line = line.strip()
            if not line.startswith("{"): continue
            try: info = json.loads(line)
            except Exception: continue
            if (info.get("duration") or 999) > max_len: continue
            from engine.refs import metrics
            m = metrics(info); m["duration"] = info.get("duration"); items.append(m)
        if not items: raise RuntimeError("search returned no short videos (YouTube may be blocking the runner)")
        items.sort(key=lambda m: (m.get("views") or 0), reverse=True)
        jsave(os.path.join(d, "search.json"), {"query": query, "time": NOW(), "ranked_by": "views", "results": items})
        done = []
        for i, m in enumerate(items[:top], 1):
            sub = os.path.join(d, f"top{i}")
            try:
                video, info = ytdlp_download(m["url"], os.path.join("in", "ref", name, f"top{i}"))
                from engine.refs import analyse
                analyse(video, sub, url=m["url"], model=E("REF_WHISPER_MODEL", "small.en"), info=info)
                for f in ("analysis.json", "transcript.txt", "hook.jpg", "frames.jpg"): changed_paths.add(os.path.join(sub, f))
                done.append(i)
            except Exception as e:
                log(f"top{i} failed: {e}")
        jsave(os.path.join(d, "status.json"), {"ok": True, "time": NOW(), "source": f"search: {query}", "analysed": done, "run": E("RUN_URL")})
    except Exception as e:
        jsave(os.path.join(d, "status.json"), {"ok": False, "time": NOW(), "source": f"search: {query}", "run": E("RUN_URL"),
                                                "error": f"{e}\n{log_tail(40)}"})

def job_selftest():
    out = "selftest/out"; os.makedirs(out, exist_ok=True)
    res = {"time": NOW(), "run": E("RUN_URL"), "stages": {}}
    st = "_st"; shutil.rmtree(st, ignore_errors=True); os.makedirs(st)
    reel = os.path.join(st, "reel")
    def stage(name, fn):
        t0 = time.time()
        try:
            v = fn(); res["stages"][name] = {"ok": True, "s": round(time.time() - t0)}
            return v
        except Exception as e:
            res["stages"][name] = {"ok": False, "s": round(time.time() - t0), "error": f"{e}\n{log_tail(50)}"}
            return None
    def make_raw():
        wav = os.path.join(st, "speech.wav")
        sh(["espeak-ng", "-v", "en-us", "-s", "155", "-w", wav, open("selftest/script.txt").read().strip()])
        rc, o = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav])
        d = float(o.strip()) + 1.5
        raw = os.path.join(st, "raw.mp4")
        sh(["ffmpeg", "-y", "-f", "lavfi", "-i", f"gradients=s=1080x1920:r=30:c0=0x2a3442:c1=0x6b5a4c:speed=0.02:d={d:.2f}",
            "-i", wav, "-filter_complex", "[1:a]apad[a]", "-map", "0:v", "-map", "[a]", "-t", f"{d:.2f}",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", raw])
        return raw
    raw = stage("make_raw", make_raw)
    if raw:
        stage("prepare", lambda: sh([sys.executable, "-m", "engine", "prepare", "--video", raw, "--out", reel,
                                     "--model", E("SELFTEST_WHISPER_MODEL", "small.en")], timeout=3600))
    tr = jload(os.path.join(reel, "transcript.json"), {})
    res["transcript"] = " ".join(w["w"] for w in tr.get("words", []))
    res["words"] = len(tr.get("words", []))
    if res["words"]:
        shutil.copytree("selftest/hf", os.path.join(reel, "hf"), dirs_exist_ok=True)
        shutil.copy("selftest/edit.json", os.path.join(reel, "edit.json"))
        b = stage("build", lambda: build("selftest", reel_dir=reel, proxy=os.path.join(reel, "proxy.mp4"))[0])
        if b:
            stage("hf_install", hf_install)
            res["hf_version"] = HF["version"]
            if HF["ready"]:
                r = stage("hyperframes", lambda: hf_check_snap_render(b, os.path.join("_out", "selftest"), "draft"))
                if r:
                    summary, render = r
                    res["check"] = summary["check"]; res["render_seconds"] = summary["render_seconds"]
                    fin = os.path.join("_out", "selftest", "final.mp4")
                    if stage("finish", lambda: sh([sys.executable, "-m", "engine", "finish", "--video", render, "--base",
                                                   os.path.join(b, "assets", "base.mp4"), "--out", fin])):
                        from engine.media import contact_sheet, probe
                        m = probe(fin); res["output"] = {"seconds": round(m["duration"], 2), "has_audio": m["has_audio"], "size": [m["width"], m["height"]]}
                        contact_sheet(fin, os.path.join(out, "sheet.jpg"), n=12, width=270, cols=4)
                for f in ("review-beats.jpg", "review-phone.jpg"):
                    src = glob.glob(os.path.join("_out", "selftest", "snaps", "**", f), recursive=True)
                    if src: shutil.copy(src[0], os.path.join(out, f))
                if os.path.exists(os.path.join("_out", "selftest", "check.json")):
                    shutil.copy(os.path.join("_out", "selftest", "check.json"), os.path.join(out, "check.json"))
    def gallery():
        """Render the technique gallery (docs/techniques) so every technique is verified by HyperFrames itself."""
        g = os.path.join(st, "gallery"); os.makedirs(g, exist_ok=True)
        shutil.copytree("docs/techniques/hf", os.path.join(g, "hf"), dirs_exist_ok=True)
        for f in ("edit.json", "transcript.json"): shutil.copy(os.path.join("docs/techniques", f), os.path.join(g, f))
        dur = float(jload(os.path.join(g, "transcript.json"))["duration"]) + 0.5
        raw = os.path.join(st, "gallery_raw.mp4")
        sh(["ffmpeg", "-y", "-f", "lavfi", "-i", f"gradients=s=1080x1920:r=30:c0=0x2a3442:c1=0x6b5a4c:speed=0.02:d={dur:.2f}",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "ultrafast",
            "-g", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", raw])
        hf_install()
        b, _ = build("gallery", reel_dir=g, proxy=raw)
        summary, render = hf_check_snap_render(b, os.path.join("_out", "gallery"), "draft")
        fin = os.path.join("_out", "gallery", "final.mp4")
        sh([sys.executable, "-m", "engine", "finish", "--video", render, "--base", os.path.join(b, "assets", "base.mp4"), "--out", fin])
        from engine.media import contact_sheet
        contact_sheet(fin, os.path.join(out, "gallery_sheet.jpg"), n=14, width=270, cols=4)
        if os.path.exists(os.path.join("_out", "gallery", "check.json")):
            shutil.copy(os.path.join("_out", "gallery", "check.json"), os.path.join(out, "gallery_check.json"))
        res["gallery"] = {"check": summary["check"], "render_seconds": summary["render_seconds"]}
        return True
    stage("gallery", gallery)
    def ytdlp_probe():
        rc, o = sh(["yt-dlp", "--simulate", "--no-playlist", "--print", "%(title)s|%(duration)s", "https://www.youtube.com/watch?v=jNQXAC9IVRw"], check=False, timeout=180)
        if rc != 0: raise RuntimeError("yt-dlp could not reach YouTube from GitHub's runner (see log)")
        return o.strip()
    res["ytdlp_youtube"] = stage("ytdlp_probe", ytdlp_probe)
    res["ok"] = all(s["ok"] for k, s in res["stages"].items() if k != "ytdlp_probe") and bool(res.get("output"))
    jsave(os.path.join(out, "result.json"), res)
    jsave("selftest/last_run.json", {"token": fhash("selftest/run.txt"), "time": NOW(), "ok": res["ok"]})
    for f in glob.glob(os.path.join(out, "*")): changed_paths.add(f)

# ------------------------------------------------------------------ what is pending
def pending():
    jobs, ev = [], E("EVENT", "")
    if ev == "workflow_dispatch" and E("INPUT_JOB", "all") not in ("", "all"):
        j, t = E("INPUT_JOB"), E("INPUT_TARGET", "")
        if j == "references":
            for name, url in queue():
                if not t or t == name: jobs.append(("references", name, url))
        else: jobs.append((j, t))
        return jobs
    if ev == "release":
        tag = E("RELEASE_TAG", "")
        if tag.startswith("ref-"): jobs.append(("ref_release", tag[4:], tag))
        elif tag: jobs.append(("prepare", tag))
    for d in sorted(glob.glob("reels/*/")):
        slug = os.path.basename(os.path.normpath(d))
        st = jload(status_path(slug), {}) or {}
        prep = os.path.join(d, "PREPARE")
        if os.path.exists(prep) and fhash(prep) != (st.get("prepare") or {}).get("token"):
            if ("prepare", slug) not in jobs: jobs.append(("prepare", slug))
            continue
        if not (os.path.exists(os.path.join(d, "transcript.json")) and os.path.exists(os.path.join(d, "hf", "index.html"))): continue
        if os.path.exists(os.path.join(d, "RENDER")):
            h = fhash(os.path.join(d, "RENDER"), os.path.join(d, "edit.json"), os.path.join(d, "transcript.json"), os.path.join(d, "hf"))
            if h != (st.get("final") or {}).get("hash"): jobs.append(("final", slug)); continue
        h = fhash(os.path.join(d, "edit.json"), os.path.join(d, "transcript.json"), os.path.join(d, "hf"))
        if h != (st.get("preview") or {}).get("hash"): jobs.append(("preview", slug))
    for name, url in queue():
        if not os.path.exists(os.path.join("references", name, "status.json")): jobs.append(("references", name, url))
    if os.path.exists("selftest/run.txt") and fhash("selftest/run.txt") != (jload("selftest/last_run.json", {}) or {}).get("token"):
        jobs.append(("selftest",))
    return jobs

def queue():
    """references/queue.txt lines:  name url   |   search name query words..."""
    out = []
    if os.path.exists("references/queue.txt"):
        for line in open("references/queue.txt", encoding="utf-8"):
            line = line.split("#", 1)[0].strip() if not line.lstrip().startswith("search") else line.strip()
            if not line or line.startswith("#"): continue
            parts = line.split()
            if parts[0] == "search" and len(parts) >= 3 and re.match(r"^[a-z0-9][a-z0-9-]*$", parts[1]):
                out.append((parts[1], "search:" + " ".join(parts[2:])))
            elif len(parts) >= 2 and re.match(r"^[a-z0-9][a-z0-9-]*$", parts[0]):
                out.append((parts[0], parts[1]))
    return out

def commit(msg):
    paths = sorted(p for p in changed_paths if os.path.exists(p))
    if not paths: log("Nothing to commit"); return
    sh(["git", "config", "user.name", "reel-bot"]); sh(["git", "config", "user.email", "reel-bot@users.noreply.github.com"])
    sh(["git", "add", "-f", *paths])
    rc, _ = sh(["git", "diff", "--cached", "--quiet"], check=False)
    if rc == 0: log("No changes"); return
    sh(["git", "commit", "-q", "-m", msg])
    br = E("BRANCH", "main")
    for i in range(6):
        if sh(["git", "pull", "-q", "--rebase", "-X", "theirs", "origin", br], check=False)[0] == 0 and \
           sh(["git", "push", "-q", "origin", f"HEAD:{br}"], check=False)[0] == 0: return
        time.sleep(5 * (i + 1))
    raise RuntimeError("could not push results")

def main():
    global LOG
    os.makedirs("_out", exist_ok=True)
    LOG = open("_out/log.txt", "a", encoding="utf-8")
    jobs = pending()
    log(f"Pending: {jobs}")
    done = []
    for j in jobs:
        kind = j[0]
        log(f"\n======== {kind} {' '.join(map(str, j[1:]))} ========")
        try:
            if kind == "prepare": job_prepare(j[1])
            elif kind == "preview": job_preview(j[1])
            elif kind == "final": job_final(j[1])
            elif kind == "references":
                if j[2].startswith("search:"): job_search(j[1], j[2][7:])
                else: job_reference(j[1], url=j[2])
            elif kind == "ref_release": job_reference(j[1], tag=j[2])
            elif kind == "selftest": job_selftest()
            done.append(" ".join(map(str, j[:2])))
        except Exception:
            log(traceback.format_exc())
    commit("reel-bot: " + (", ".join(done) or "no-op"))

if __name__ == "__main__":
    main()
