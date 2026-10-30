"""Local preview in Claude's sandbox: build the project (tokens resolved), load it in Chromium with a
small HyperFrames-like runtime, and snapshot chosen times into a contact sheet. Approximate: the
footage is a stand-in and HyperFrames' own check/render on GitHub is the source of truth."""
import functools, glob, http.server, json, os, socketserver, subprocess, threading
from .edit import build_project, load_edit
from .fonts import install_fonts
from .util import ReelError, font_path

HERE = os.path.dirname(os.path.abspath(__file__))

def _gsap_source():
    """GSAP ships inside the HyperFrames repo (registry assets). Clone once if missing."""
    cands = glob.glob(os.path.expanduser("~/.cache/reel_engine/hyperframes/registry/blocks/*/assets/gsap-*.min.js"))
    if not cands:
        dest = os.path.expanduser("~/.cache/reel_engine/hyperframes")
        if not os.path.exists(dest):
            subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/heygen-com/hyperframes.git", dest], check=True, capture_output=True, env={**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"})
        cands = glob.glob(os.path.join(dest, "registry/blocks/*/assets/gsap-*.min.js"))
    if not cands: raise ReelError("GSAP not found in the HyperFrames clone")
    return open(sorted(cands)[-1], encoding="utf-8").read()

def _standin(path, w, h):
    from PIL import Image, ImageDraw, ImageFilter
    im = Image.new("RGB", (w, h), (46, 52, 64)); d = ImageDraw.Draw(im)
    for y in range(h):
        k = y / h; d.line([(0, y), (w, y)], fill=(int(46 + 50 * k), int(52 + 30 * k), int(64 + 10 * k)))
    cx, cy = w // 2, int(h * 0.47)
    d.ellipse((cx - 210, cy - 270, cx + 210, cy + 270), fill=(120, 96, 86))          # head
    d.rounded_rectangle((cx - 420, cy + 260, cx + 420, h + 200), radius=260, fill=(70, 74, 92))  # shoulders
    im = im.filter(ImageFilter.GaussianBlur(3)); im.save(path)

class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def snapshot(reel_dir, build_dir, times, out_sheet, cols=4, tile_w=270):
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageDraw, ImageFont
    edit = load_edit(reel_dir)
    os.makedirs(os.path.join(build_dir, "assets"), exist_ok=True)
    ff = install_fonts(edit.get("fonts", []), os.path.join(build_dir, "assets"))
    tl, warn = build_project(reel_dir, build_dir, fontfaces=ff)
    W, H = 1080, 1920
    standin = os.path.join(build_dir, "assets", "_standin.png"); _standin(standin, W, H)
    handler = functools.partial(_Quiet, directory=build_dir)
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    shots, logs = [], []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
            pg.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
            pg.add_init_script(_gsap_source())
            pg.add_init_script(open(os.path.join(HERE, "lib", "harness.js"), encoding="utf-8").read())
            pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="load")
            info = pg.evaluate("s => window.__hfInit(s)", "assets/_standin.png")
            for t in times:
                pg.evaluate("t => window.__hfSeek(t)", t)
                pg.wait_for_timeout(60)
                path = os.path.join(build_dir, f"_snap_{t:07.2f}.png")
                pg.screenshot(path=path, clip={"x": 0, "y": 0, "width": W, "height": H})
                shots.append((t, path))
            errors = pg.evaluate("() => window.__hfErrors")
            b.close()
    finally:
        srv.shutdown()
    fnt = ImageFont.truetype(font_path("mono"), 18)
    th = int(tile_w * H / W)
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tile_w + 6) + 6, rows * (th + 6) + 6), (12, 14, 20))
    for i, (t, pth) in enumerate(shots):
        im = Image.open(pth).convert("RGB").resize((tile_w, th), Image.LANCZOS)
        d = ImageDraw.Draw(im); d.rectangle((0, th - 26, 92, th), fill=(0, 0, 0)); d.text((6, th - 24), f"{t:6.2f}s", fill=(255, 255, 255), font=fnt)
        sheet.paste(im, (6 + (i % cols) * (tile_w + 6), 6 + (i // cols) * (th + 6)))
    sheet.save(out_sheet, quality=88)
    return {"duration": tl.duration, "comps": info["comps"], "errors": errors + [l for l in logs if "favicon" not in l],
            "warnings": warn, "frames": [p for _, p in shots]}
