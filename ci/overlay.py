"""Final = Swati's ORIGINAL video, untouched, with only the edit layered on top (Swati, 12 Nov 2026).

Why: the old final re-rendered a 1080p/30fps, colour-converted copy of her iPhone video, so every Reel lost
resolution, frame rate and colour. Now the composition is rendered as transparent GRAPHICS ONLY, and FFmpeg lays it
on the raw upload at its own resolution, frame rate, HDR transfer and audio:

  raw upload (4K60 HLG)  ->  cut to the timeline (same keeps as the preview)          = picture + sound, never graded
  [under layer]          ->  scenes marked data-layer="under" (news backgrounds behind her), drawn over the raw
  [her, matte]           ->  raw again, masked by the person matte (from the shared cutout), so she stays in front
  [over layer]           ->  every other scene + captions on top

Graphics are converted from sRGB to the raw's colour space only (HLG: SDR white -> HLG reference white 75%, BT.2408).
The raw pixels themselves are only decoded and re-encoded (HEVC 10-bit, high quality) - no tone mapping, no scaling,
no fps change, no loudness change. Audio is stream-copied when nothing is cut.

Opt-outs live in edit.json "final": {"mode": "rerender"} brings back the old full re-render.
Shared work: the person matte comes from the cutout cached on the release (one per upload+cuts), reused by every
variant; the raw download is cached per run.
"""
import json, os, re, shutil, subprocess, sys, time

HDR_TRC = ("arib-std-b67", "smpte2084")

def probe(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                                  capture_output=True, text=True, check=True).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd: rot = int(float(sd["rotation"]))
    rot = int(float((v.get("tags") or {}).get("rotate", rot) or rot))
    if abs(rot) in (90, 270): w, h = h, w
    num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den) if float(den or 0) else 30.0
    return {"w": w, "h": h, "fps": fps, "fps_str": v.get("r_frame_rate") or f"{fps:g}",
            "trc": v.get("color_transfer") or "", "prim": v.get("color_primaries") or "",
            "matrix": v.get("color_space") or "", "pix_fmt": v.get("pix_fmt") or "",
            "audio": a is not None, "acodec": (a or {}).get("codec_name"), "duration": float(j["format"]["duration"])}

# ---------------------------------------------------------------- graphics-only HyperFrames project
HIDE_MEDIA = """
<style id="hf-overlay-mode">
  html, body, #root { background: transparent !important; }
  video, #cam, #cutcam, #base, #cut { visibility: hidden !important; }
  %s
</style>
"""

def overlay_project(build_dir, out_dir, layer):
    """Copy the built HyperFrames project and turn it into ONE transparent graphics layer.
    layer "over": everything except hosts marked data-layer="under"; layer "under": only those hosts."""
    if os.path.exists(out_dir): shutil.rmtree(out_dir)
    shutil.copytree(build_dir, out_dir, ignore=shutil.ignore_patterns("base.mp4", "cutout.webm", "*.mp4", "*.mov", "*.webm"))
    p = os.path.join(out_dir, "index.html")
    html = open(p, encoding="utf-8").read()
    # drop the footage elements entirely so the renderer never decodes video for a graphics layer
    html = re.sub(r"<video\b[^>]*>\s*</video>", "", html, flags=re.S)
    under_ids = re.findall(r'<div[^>]*\bid="([^"]+)"[^>]*\bdata-layer="under"', html) + \
                re.findall(r'<div[^>]*\bdata-layer="under"[^>]*\bid="([^"]+)"', html)
    under_ids = sorted(set(under_ids))
    if layer == "under":
        keep = set(under_ids)
        hosts = re.findall(r'<div[^>]*\bid="([^"]+)"[^>]*data-composition-src=', html)
        hide = [h for h in hosts if h not in keep]
    else:
        hide = under_ids
    rule = (", ".join(f"#{h}" for h in hide) + " { visibility: hidden !important; }") if hide else ""
    html = html.replace("</head>", HIDE_MEDIA % rule + "</head>", 1)
    open(p, "w", encoding="utf-8").write(html)
    return under_ids

def has_under(build_dir):
    html = open(os.path.join(build_dir, "index.html"), encoding="utf-8").read()
    return 'data-layer="under"' in html

# ---------------------------------------------------------------- compositing onto the raw upload
def _graphics_chain(label_in, label_out, W, H, fps_str, hdr):
    """RGBA graphics -> raw's size/fps/colour space, alpha kept."""
    if hdr:
        conv = ("format=gbrp16le,zscale=tin=iec61966-2-1:pin=bt709:min=gbr:rin=full:"
                "p=bt2020:t=arib-std-b67:m=bt2020nc:r=tv:npl=203,format=yuv444p10le")
        af, merged = "gray10le", "yuva444p10le"
    else:
        conv = "format=gbrp,zscale=min=gbr:rin=full:m=bt709:r=tv,format=yuv444p"
        af, merged = "gray", "yuva444p"
    return (f"[{label_in}]scale={W}:{H}:flags=lanczos,format=gbrap16le,split[{label_out}c0][{label_out}a0];"
            f"[{label_out}c0]{conv}[{label_out}c];"
            f"[{label_out}a0]alphaextract,format={af}[{label_out}a];"
            f"[{label_out}c][{label_out}a]alphamerge,format={merged},fps={fps_str}[{label_out}]")

def compose(raw, out, keeps=None, speed=1.0, over=None, under=None, matte=None, crf=14, preset="ultrafast",
            log=print):
    """Lay graphics on the raw video. keeps: [[a,b],...] on the raw clock (None = whole video).
    matte: transparent video of her (any size/fps), used only where an under layer exists."""
    m = probe(raw)
    W, H, fps_str = m["w"], m["h"], m["fps_str"]
    hdr = m["trc"] in HDR_TRC
    inputs = ["-i", raw]
    idx = {}
    for name, path in (("over", over), ("under", under), ("matte", matte)):
        if path:
            if path.endswith(".webm"): inputs += ["-c:v", "libvpx-vp9"]   # decode VP9 alpha
            inputs += ["-i", path]; idx[name] = len(idx) + 1
    fc = []
    whole = not keeps or (len(keeps) == 1 and keeps[0][0] <= 0.001 and keeps[0][1] >= m["duration"] - 0.05)
    sp = float(speed or 1.0)
    cut_audio = not whole or abs(sp - 1) > 1e-3
    # 1) the raw picture (+audio) cut to the timeline
    if whole:
        fc.append("[0:v]null[rv]")
    else:
        parts = []
        for i, (a, b) in enumerate(keeps):
            fc.append(f"[0:v]trim=start={a:.4f}:end={b:.4f},setpts=PTS-STARTPTS[v{i}]")
            if m["audio"]:
                fc.append(f"[0:a]atrim=start={a:.4f}:end={b:.4f},asetpts=PTS-STARTPTS,"
                          f"afade=t=in:d=0.015,afade=t=out:st={max(0, b - a - 0.02):.3f}:d=0.02[a{i}]")
                parts.append(f"[v{i}][a{i}]")
            else:
                parts.append(f"[v{i}]")
        n = len(keeps)
        fc.append("".join(parts) + f"concat=n={n}:v=1:a={1 if m['audio'] else 0}[rv0]" + ("[ra0]" if m["audio"] else ""))
        fc.append("[rv0]null[rv]")
    if abs(sp - 1) > 1e-3:
        fc.append(f"[rv]setpts=PTS/{sp:.4f}[rvs]"); rv = "rvs"
    else:
        rv = "rv"
    if cut_audio and m["audio"]:
        src = "[ra0]" if not whole else "[0:a]"
        fc.append(f"{src}" + (f"atempo={sp:.4f}," if abs(sp - 1) > 1e-3 else "") + "anull[ra]")
    cur = rv
    pix = os.environ.get("OVERLAY_PIX") or ("yuv420p10" if hdr else "yuv420")
    # 2) under layer (behind her) + her, cut out by the matte
    if "under" in idx:
        fc.append(_graphics_chain(f"{idx['under']}:v", "gu", W, H, fps_str, hdr))
        if "matte" in idx:
            fc.append(f"[{cur}]split[base0][her0]")
            mf = "gray10le" if hdr else "gray"
            fc.append(f"[{idx['matte']}:v]format=yuva420p,alphaextract,scale={W}:{H}:flags=bicubic,fps={fps_str},format={mf}[mt]")
            fc.append(f"[her0]format={'yuv444p10le' if hdr else 'yuv444p'}[her1];[her1][mt]alphamerge[her]")
            fc.append(f"[base0][gu]overlay=format={pix}:eof_action=pass:shortest=0[bg]")
            fc.append(f"[bg][her]overlay=format={pix}:eof_action=pass:shortest=0[mid]")
            cur = "mid"
        else:
            fc.append(f"[{cur}][gu]overlay=format={pix}:eof_action=pass:shortest=0[mid]"); cur = "mid"
    # 3) over layer (captions, cards, titles)
    if "over" in idx:
        fc.append(_graphics_chain(f"{idx['over']}:v", "go", W, H, fps_str, hdr))
        fc.append(f"[{cur}][go]overlay=format={pix}:eof_action=pass:shortest=0[top]"); cur = "top"
    fc.append(f"[{cur}]format={'yuv420p10le' if hdr else 'yuv420p'}[vout]")
    script = out + ".fc.txt"; open(script, "w").write(";\n".join(fc))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-stats_period", "5"] + inputs + ["-filter_complex_script", script,
           "-map", "[vout]"]
    if m["audio"]:
        if cut_audio: cmd += ["-map", "[ra]", "-c:a", "aac", "-b:a", "256k"]
        else: cmd += ["-map", "0:a:0", "-c:a", "copy"]
    if hdr:
        prim = m["prim"] or "bt2020"; trc = m["trc"]; mat = m["matrix"] or "bt2020nc"
        x265 = f"log-level=error:colorprim={prim}:transfer={trc}:colormatrix={mat}:range=limited"
        cmd += ["-c:v", "libx265", "-preset", preset, "-crf", str(crf), "-x265-params", x265,
                "-color_primaries", prim, "-color_trc", trc, "-colorspace", mat, "-color_range", "tv", "-tag:v", "hvc1"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(max(10, crf - 2)), "-pix_fmt", "yuv420p"]
        for flag, val in (("-color_primaries", m["prim"]), ("-color_trc", m["trc"]), ("-colorspace", m["matrix"])):
            if val and val != "unknown": cmd += [flag, val]
    cmd += ["-movflags", "+faststart", out]
    log("$ " + " ".join(cmd))
    t0 = time.time()
    # stream FFmpeg's progress lines into the job log so Swati can watch it on GitHub
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        line = line.rstrip()
        if line: log("  " + line)
    if p.wait() != 0: raise RuntimeError(f"compose failed (exit {p.returncode})")
    os.remove(script)
    return {"seconds": round(time.time() - t0), "hdr": hdr, "size": [W, H], "fps": fps_str,
            "audio": "copied" if (m["audio"] and not cut_audio) else ("re-encoded (cut)" if m["audio"] else "none")}

def thumbnail(video, out, t=0.0, width=1080):
    """cover.jpg: a still for picking/sharing only (the Reel itself stays HDR)."""
    m = probe(video)
    vf = f"scale={width}:-2"
    if m["trc"] in HDR_TRC:
        vf = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=mobius:desat=0,"
              "zscale=t=bt709:m=bt709:r=tv,format=yuv420p," + vf)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", vf,
                    "-q:v", "2", out], check=True)

if __name__ == "__main__":
    # local test: python3 ci/overlay.py raw over.mov out.mov [under.mov matte.webm] [keeps-json]
    a = sys.argv[1:]
    keeps = json.loads(a[5]) if len(a) > 5 else None
    print(compose(a[0], a[2], keeps=keeps, over=a[1], under=a[3] if len(a) > 3 else None,
                  matte=a[4] if len(a) > 4 else None))

# ---------------------------------------------------------------- pipeline integration (used by ci/vrun.py)
CAM_MOVE = re.compile(r'\(\s*["\']#cam["\']\s*,\s*\{([^}]*)\}')

def camera_moves(build_dir):
    """True if the composition moves/zooms/crops the footage (#cam): those can't be laid over the raw yet."""
    html = open(os.path.join(build_dir, "index.html"), encoding="utf-8").read()
    for body in CAM_MOVE.findall(html):
        for k, v in re.findall(r"\b(scale|x|y|clipPath|rotation)\s*:\s*([^,}]+)", body):
            v = v.strip().strip('"\'')
            if k == "scale" and v in ("1", "1.0"): continue
            if k in ("x", "y", "rotation") and v in ("0", "0.0"): continue
            if k == "clipPath" and "inset(0px 0px 0px 0px" in v: continue
            return True
    return False

def matte_key(J, slug):
    """One person-cutout per upload + cut list, shared by every variant and by preview and final."""
    import hashlib
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from engine.edit import Timeline, load_edit
    d = os.path.join("reels", slug); edit = load_edit(d)
    tl = Timeline(os.path.join(d, "transcript.json"), edit)
    rel = (edit.get("release") or slug)
    blob = json.dumps({"rel": rel, "keeps": tl.keeps, "speed": tl.speed, "hdr": edit.get("hdr") or "tonemap"}, sort_keys=True)
    return "cutout-" + hashlib.sha256(blob.encode()).hexdigest()[:16] + ".webm"

def shared_cutout(J, slug, build_dir, opt=True):
    """Replacement for bgjobs.bg_cutout: cache key from the timeline (stable), not from base.mp4 bytes
    (re-encodes are not byte-identical, which silently forced a second 35-minute cutout on 12 Nov 2026)."""
    dest = os.path.join(build_dir, "assets", "cutout.webm")
    name = matte_key(J, slug)
    cache = os.path.join("_work", slug); os.makedirs(cache, exist_ok=True)
    if any(n == name for n, _ in J.release_assets(slug)):
        J.log(f"reusing shared cutout {name}")
        shutil.copy(J.download_asset(slug, name, cache), dest)
        return dest
    t0 = time.time()
    q = ["--quality", "best"] if isinstance(opt, dict) and opt.get("quality") == "best" else []
    J.sh(["hyperframes", "remove-background", os.path.join(build_dir, "assets", "base.mp4"), "-o", dest, *q, "--json"],
         timeout=int(J.E("BG_TIMEOUT", "10800")))
    J.log(f"remove-background took {round(time.time() - t0)} s")
    shutil.copy(dest, os.path.join(cache, name)); J.upload(slug, os.path.join(cache, name))
    return dest

def render_layer(J, layer_dir, out, fps=30, res=None):
    cmd = ["hyperframes", "render", "--format", "mov", "--fps", str(fps), "--output", os.path.abspath(out)]
    if res: cmd += ["--resolution", res]
    J.sh(cmd, cwd=layer_dir, timeout=int(J.E("RENDER_TIMEOUT", "7200")))
    return out

def sheet(video, out, n=16, cols=4, width=270):
    """Review contact sheet that shows HDR the way a phone does (tone-mapped stills, the video itself is untouched)."""
    from PIL import Image, ImageDraw
    m = probe(video); tmp = out + "_f"; os.makedirs(tmp, exist_ok=True)
    ims = []
    for i in range(n):
        t = m["duration"] * (i + 0.5) / n; p = os.path.join(tmp, f"{i:02d}.jpg")
        thumbnail(video, p, t, width); ims.append((t, p))
    w, h = Image.open(ims[0][1]).size
    g = Image.new("RGB", (cols * w, ((n + cols - 1) // cols) * h)); d = ImageDraw.Draw(g)
    for i, (t, p) in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * h; g.paste(Image.open(p), (x, y))
        d.rectangle((x, y, x + 60, y + 18), fill=(0, 0, 0)); d.text((x + 4, y + 3), f"{t:5.1f}s", fill=(255, 255, 255))
    g.save(out, quality=78); shutil.rmtree(tmp, ignore_errors=True)

def job_final_overlay(J, slug):
    d = os.path.join("reels", slug)
    h = J.fhash(os.path.join(d, "RENDER"), os.path.join(d, "edit.json"), os.path.join(d, "transcript.json"), os.path.join(d, "hf"))
    try:
        J.hf_install()
        edit = J.jload(os.path.join(d, "edit.json"), {}) or {}
        fin = edit.get("final") or {}
        b = os.path.abspath(os.path.join("_build", slug))
        # graphics only need the timeline; the cutout needs the small base video (shared, cached on the release)
        need_matte = bool(edit.get("bg_remove"))
        proxy = J.get_proxy(slug) if need_matte else None
        sys.path.insert(0, os.getcwd())
        J.sh([sys.executable, "-m", "engine", "build", "--reel", d, "--out", b] + (["--proxy", proxy] if proxy else []), timeout=3600)
        J.hf_add(b, edit.get("hf_add"))
        if camera_moves(b) and fin.get("mode") != "overlay-force":
            J.log("composition moves the footage (#cam): overlay final can't reproduce camera moves yet -> full re-render")
            return J._job_final_rerender(slug)
        matte = shared_cutout(J, slug, b, edit.get("bg_remove")) if need_matte and has_under(b) else None
        out = os.path.join("_out", slug); os.makedirs(out, exist_ok=True)
        rc, chk = J.sh("hyperframes check --json", cwd=b, check=False, timeout=900)
        summary = {"check": J.summarize_check(chk), "hf_version": J.HF["version"], "mode": "overlay-on-original"}
        res = fin.get("graphics_res")          # None = composition size (1080x1920); "portrait-4k" for 4K graphics
        gfps = int(fin.get("graphics_fps", 30))
        t0 = time.time()
        over = render_layer(J, overlay_project_dir(b, "over"), os.path.join(out, "over.mov"), gfps, res)
        under = render_layer(J, overlay_project_dir(b, "under"), os.path.join(out, "under.mov"), gfps, res) if has_under(b) else None
        summary["graphics_seconds"] = round(time.time() - t0)
        raw = J.download_asset(slug, raw_name(J, slug), os.path.join("in", slug))
        tl = json.load(open(os.path.join(b, "timeline.json")))
        final = os.path.join(out, "final_reel.mp4")
        info = compose(raw, final, keeps=tl["keeps"], speed=tl.get("speed", 1.0), over=over, under=under, matte=matte,
                       crf=int(fin.get("crf", 14)), preset=fin.get("preset", "ultrafast"), log=J.log)
        summary["compose"] = info
        cover = os.path.join(out, "cover.jpg"); thumbnail(final, cover, float(edit.get("cover_at", 0.0)))
        files = [final, cover]
        post = edit.get("post") or {}
        if post.get("caption") or post.get("hashtags"):
            cap = os.path.join(out, "caption.txt")
            open(cap, "w", encoding="utf-8").write((post.get("caption", "").strip() + "\n\n" + " ".join(post.get("hashtags", []))).strip() + "\n")
            files.append(cap)
        J.upload(slug, *files)
        rv = os.path.join(d, "review"); os.makedirs(rv, exist_ok=True)
        sheet(final, os.path.join(rv, "sheet.jpg")); shutil.copy(cover, os.path.join(rv, "cover.jpg"))
        for f in ("sheet.jpg", "cover.jpg"): J.changed_paths.add(os.path.join(rv, f))
        m = probe(final)
        name = os.path.basename(final)
        try:
            import variants; name = variants.vname(slug, name); relname = variants.release_of(slug)
        except Exception: relname = slug
        J.set_status(slug, "final", True, {"hash": h, **summary, "seconds": round(m["duration"], 2),
                                          "size": [m["w"], m["h"]], "fps": m["fps_str"], "transfer": m["trc"],
                                          "size_mb": round(os.path.getsize(final) / 1e6, 1),
                                          "video": f"{J.E('REPO_URL')}/releases/download/{relname}/{name}"})
    except Exception as e:
        J.set_status(slug, "final", False, {"hash": h}, err=f"{e}\n{J.log_tail()}")

def raw_name(J, slug):
    """The uploaded file itself (recorded at prepare), never a bigger generated file on the same release."""
    try:
        import variants; rel = variants.release_of(slug)
    except Exception: rel = slug
    st = J.jload(J.status_path(rel), {}) or {}
    return ((st.get("prepare") or {}).get("raw")) or J.raw_asset(slug)

def overlay_project_dir(build_dir, layer):
    out = build_dir + "_" + layer
    overlay_project(build_dir, out, layer)
    return out
