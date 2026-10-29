"""Shared pieces: tools, fonts, palette, drawing helpers and the icon set."""
import os, io, re, sys, json, math, random, shutil, struct, subprocess, zipfile, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
CACHE = os.environ.get("REEL_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "reel_engine"))


# ------------------------------------------------------------------ tools
class ReelError(RuntimeError):
    pass

def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=quiet, text=True)
    if r.returncode != 0:
        tail = (r.stderr or "")[-2500:] if quiet else ""
        raise ReelError("Command failed: " + " ".join(cmd)[:400] + "\n" + tail)
    return r.stdout if quiet else ""

def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    j = json.loads(out)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if v is None: raise ReelError(f"{path} has no video stream")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd: rot = int(sd["rotation"])
    rot = int(v.get("tags", {}).get("rotate", rot) or rot)
    if abs(rot) in (90, 270): w, h = h, w
    num, den = (v.get("avg_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    return {"width": w, "height": h, "fps": round(fps, 3), "codec": v.get("codec_name"),
            "transfer": v.get("color_transfer", ""), "duration": float(j["format"]["duration"]),
            "has_audio": a is not None, "size_mb": round(int(j["format"].get("size", 0)) / 1e6, 1)}


# ------------------------------------------------------------------ fonts
FONT_ZIPS = [
    ("https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip", ["extras/ttf/Inter-Black.ttf"]),
    ("https://github.com/floriankarsten/space-grotesk/releases/download/2.0.0/SpaceGrotesk-2.0.0.zip",
     ["ttf/static/SpaceGrotesk-Bold.ttf"]),
    ("https://github.com/adobe-fonts/source-serif/releases/download/4.005R/source-serif-4.005_Desktop.zip",
     ["TTF/SourceSerif4-Bold.ttf"]),
    ("https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip",
     ["fonts/ttf/JetBrainsMono-Bold.ttf"]),
]
FONTS = os.path.join(CACHE, "fonts")
F_TITLE = os.path.join(FONTS, "SpaceGrotesk-Bold.ttf")
F_CAP = os.path.join(FONTS, "Inter-Black.ttf")
F_SERIF = os.path.join(FONTS, "SourceSerif4-Bold.ttf")
F_MONO = os.path.join(FONTS, "JetBrainsMono-Bold.ttf")
# the names libass knows them by
N_TITLE, N_CAP, N_SERIF, N_MONO = "Space Grotesk Bold", "Inter Black", "Source Serif 4 Bold", "JetBrains Mono Bold"

def ensure_fonts():
    os.makedirs(FONTS, exist_ok=True)
    for url, members in FONT_ZIPS:
        need = [m for m in members if not os.path.exists(os.path.join(FONTS, os.path.basename(m)))]
        if not need: continue
        try:
            z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url, timeout=180).read()))
        except Exception as e:
            raise ReelError(f"Could not download fonts from {url} ({e})")
        for m in need:
            name = next(n for n in z.namelist() if (n.endswith("/" + m) or n == m) and "__MACOSX" not in n)
            open(os.path.join(FONTS, os.path.basename(m)), "wb").write(z.read(name))


# ------------------------------------------------------------------ palette (style presets)
class P:
    """Current palette. Style presets overwrite these attributes."""
    night, cyan, violet = "#070A12", "#3DE0FF", "#7C5CFF"
    red, green, white, paper, amber, grey = "#FF3B4E", "#2EE59D", "#F2F4F7", "#F4F1EA", "#FFC53D", "#7A8394"

STYLES = {
    # calm security-briefing look used for Black October
    "briefing": {},
    # same system, warmer accent for demos and how-tos
    "demo": {"cyan": "#5BE7C4", "violet": "#FF8A3D"},
}

def apply_style(name, overrides=None):
    for k, v in {**STYLES.get(name or "briefing", {}), **(overrides or {})}.items():
        setattr(P, k, v)

def colour(c):
    """'red' / 'green' / '#hex' -> '#hex'."""
    if c is None: return P.white
    return getattr(P, c, c) if not str(c).startswith("#") else c

def hexrgb(h, a=255):
    h = colour(h)
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)

def ass_col(h, alpha=None):
    h = colour(h); r, g, b = h[1:3], h[3:5], h[5:7]
    return f"&H{b}{g}{r}&" if alpha is None else f"&H{alpha:02X}{b}{g}{r}"


# ------------------------------------------------------------------ easing
def ease(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)

def spring(x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    return 1 - math.exp(-6 * x) * math.cos(9 * x)

def appear(t, t0, d=0.3): return ease((t - t0) / d)
def window(t, t0, t1, fin=0.3, fout=0.25): return ease((t - t0) / fin) * (1 - ease((t - (t1 - fout)) / fout))


# ------------------------------------------------------------------ drawing helpers
_fc = {}
def font(path, px):
    """A font for drawing at 2x (px = size on the final 1080-wide frame)."""
    k = (path, round(px * 2))
    if k not in _fc: _fc[k] = ImageFont.truetype(path, round(px * 2))
    return _fc[k]

def tw(path, px, text): return font(path, px).getlength(text) / 2

def em_scale(path):
    """ASS font size -> real em size, the way libass does it (OS/2 win metrics)."""
    d = open(path, "rb").read()
    tables = {d[12 + i * 16:16 + i * 16]: struct.unpack(">I", d[20 + i * 16:24 + i * 16])[0]
              for i in range(struct.unpack(">H", d[4:6])[0])}
    upm = struct.unpack(">H", d[tables[b"head"] + 18:tables[b"head"] + 20])[0]
    o = tables[b"OS/2"]; asc, desc = struct.unpack(">HH", d[o + 74:o + 78])
    return upm / (asc + desc)

_ms = {}
def ass_text_w(path, size, text):
    """Width in px of text at an ASS font size."""
    if path not in _ms: _ms[path] = (ImageFont.truetype(path, 200), em_scale(path))
    f, k = _ms[path]
    return f.getlength(text) * size * k / 200

def tint(mask, col, alpha=1.0):
    layer = Image.new("RGBA", mask.size, hexrgb(col, 0))
    layer.putalpha(mask.point(lambda v: int(v * alpha))); return layer

def fade_img(img, a):
    if a >= 0.999: return img
    img = img.copy(); img.putalpha(img.getchannel("A").point(lambda v: int(v * max(0.0, a)))); return img

def paste(frame, img, cx, cy, alpha=1.0, scale=1.0):
    if alpha <= 0.01 or scale <= 0.01: return
    if abs(scale - 1) > 0.002:
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.BICUBIC)
    img = fade_img(img, alpha)
    frame.alpha_composite(img, (round(cx - img.width / 2), round(cy - img.height / 2)))

def sprite(w, h, fn):
    """Draw fn(d, s, im) at 2x on a w x h canvas and return it smoothed to 1x."""
    im = Image.new("RGBA", (max(1, round(w)) * 2, max(1, round(h)) * 2), (0, 0, 0, 0))
    fn(ImageDraw.Draw(im), 2, im)
    return im.resize((max(1, round(w)), max(1, round(h))), Image.LANCZOS)

def with_shadow(img, blur=14, alpha=0.6, dy=10):
    m = blur * 3
    out = Image.new("RGBA", (img.width + 2 * m, img.height + 2 * m + dy), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0); sh.paste(img.getchannel("A"), (m, m + dy))
    out.alpha_composite(tint(sh.filter(ImageFilter.GaussianBlur(blur)), P.night, alpha))
    out.alpha_composite(img, (m, m)); return out

def txt(d, s, x, y, text, path, px, col, anchor="la", alpha=255):
    d.text((x * s, y * s), text, font=font(path, px), fill=hexrgb(col, alpha), anchor=anchor)

def panel(d, s, x0, y0, x1, y1, r=26, fill=None, a=225, border=None, ba=150, bw=2):
    d.rounded_rectangle((x0 * s, y0 * s, x1 * s, y1 * s), radius=r * s, fill=hexrgb(fill or P.night, a),
                        outline=hexrgb(border, ba) if border else None, width=bw * s if border else 0)

def wrap(path, px, text, width):
    out, line = [], ""
    for w in text.split():
        test = (line + " " + w).strip()
        if tw(path, px, test) <= width or not line: line = test
        else: out.append(line); line = w
    return out + [line]


# ------------------------------------------------------------------ icons
ICONS = ["building", "card", "fridge", "shield", "shield_check", "lock", "lock_open", "code", "power", "folder",
         "key", "server", "browser", "globe", "hourglass", "chip", "wrench", "calendar", "drop", "video", "bolt",
         "house", "alert", "user", "cloud", "eye", "chart", "mail", "phone", "bug", "link", "search", "check",
         "cross", "wifi", "money", "terminal"]

def icon(d, s, name, X, Y, size, col, alpha=255):
    """Simple line/fill icons in a 100x100 box at (X, Y), size px wide. Unknown names fall back to 'alert'."""
    u = size / 100; c = hexrgb(col, alpha); bg = hexrgb(P.night)
    lw = max(2, round(size * 0.08)) * s
    def Pt(x, y): return ((X + x * u) * s, (Y + y * u) * s)
    def box(x0, y0, x1, y1): return (*Pt(x0, y0), *Pt(x1, y1))
    def line(*pts, w=1.0): d.line([c for p in pts for c in Pt(*p)], fill=c, width=round(lw * w), joint="curve")
    n = name if name in ICONS else "alert"
    if n == "building":
        d.polygon([Pt(8, 36), Pt(50, 8), Pt(92, 36)], fill=c)
        for cx in (18, 36, 54, 72): d.rectangle(box(cx, 42, cx + 10, 80), fill=c)
        d.rectangle(box(8, 84, 92, 94), fill=c)
    elif n == "card":
        d.rounded_rectangle(box(6, 20, 94, 80), radius=10 * u * s, outline=c, width=lw)
        d.rectangle(box(6, 34, 94, 46), fill=c); d.rectangle(box(16, 58, 38, 68), fill=c)
    elif n == "fridge":
        d.rounded_rectangle(box(22, 4, 78, 96), radius=10 * u * s, outline=c, width=lw)
        line((22, 38), (78, 38)); line((66, 14), (66, 28)); line((66, 48), (66, 70))
    elif n in ("shield", "shield_check"):
        d.polygon([Pt(50, 2), Pt(90, 16), Pt(88, 50), Pt(72, 78), Pt(50, 96), Pt(28, 78), Pt(12, 50), Pt(10, 16)], fill=c)
        if n == "shield_check":
            d.line((*Pt(30, 50), *Pt(45, 65), *Pt(72, 34)), fill=bg, width=round(lw * 1.6), joint="curve")
    elif n in ("lock", "lock_open"):
        d.rounded_rectangle(box(18, 44, 82, 94), radius=8 * u * s, fill=c)
        if n == "lock":
            d.arc(box(30, 10, 70, 56), 180, 360, fill=c, width=lw); line((30, 33), (30, 46)); line((70, 33), (70, 46))
        else:
            d.arc(box(52, 2, 92, 48), 180, 360, fill=c, width=lw); line((52, 25), (52, 46))
    elif n == "code":
        line((34, 24), (10, 50), (34, 76)); line((66, 24), (90, 50), (66, 76)); line((58, 16), (42, 84))
    elif n == "terminal":
        d.rounded_rectangle(box(4, 14, 96, 86), radius=10 * u * s, outline=c, width=lw)
        line((20, 36), (36, 50), (20, 64)); line((44, 66), (70, 66))
    elif n == "power":
        d.arc(box(14, 16, 86, 88), 300, 240, fill=c, width=lw); line((50, 6), (50, 48))
    elif n == "folder":
        d.polygon([Pt(6, 20), Pt(38, 20), Pt(46, 30), Pt(94, 30), Pt(94, 84), Pt(6, 84)], fill=c)
    elif n == "key":
        d.ellipse(box(4, 30, 44, 70), outline=c, width=round(lw * 1.3))
        line((44, 50), (96, 50), w=1.3); line((78, 50), (78, 68), w=1.2); line((90, 50), (90, 64), w=1.2)
    elif n == "server":
        for y0 in (8, 38, 68):
            d.rounded_rectangle(box(10, y0, 90, y0 + 24), radius=6 * u * s, outline=c, width=lw)
            d.ellipse(box(20, y0 + 8, 28, y0 + 16), fill=c)
    elif n == "browser":
        d.rounded_rectangle(box(6, 14, 94, 86), radius=10 * u * s, outline=c, width=lw); line((6, 34), (94, 34))
        for x0 in (16, 28, 40): d.ellipse(box(x0, 21, x0 + 7, 28), fill=c)
    elif n == "globe":
        d.ellipse(box(6, 6, 94, 94), outline=c, width=lw); d.ellipse(box(30, 6, 70, 94), outline=c, width=lw)
        line((6, 50), (94, 50))
    elif n == "hourglass":
        line((20, 6), (80, 6)); line((20, 94), (80, 94))
        line((28, 6), (28, 22), (50, 50), (28, 78), (28, 94)); line((72, 6), (72, 22), (50, 50), (72, 78), (72, 94))
        d.polygon([Pt(36, 86), Pt(64, 86), Pt(50, 70)], fill=c)
    elif n == "chip":
        d.rounded_rectangle(box(24, 24, 76, 76), radius=8 * u * s, outline=c, width=lw)
        for p in (38, 62):
            line((p, 6), (p, 24)); line((p, 76), (p, 94)); line((6, p), (24, p)); line((76, p), (94, p))
        d.text(Pt(50, 51), "AI", font=font(F_MONO, size * 0.24), fill=c, anchor="mm")
    elif n == "wrench":
        line((16, 84), (58, 42), w=1.8); d.arc(box(50, 10, 92, 52), 120, 400, fill=c, width=round(lw * 1.4))
    elif n == "calendar":
        d.rounded_rectangle(box(8, 16, 92, 92), radius=8 * u * s, outline=c, width=lw)
        d.rectangle(box(8, 16, 92, 38), fill=c); line((30, 4), (30, 24)); line((70, 4), (70, 24))
    elif n == "drop":
        d.polygon([Pt(50, 4), Pt(25, 54), Pt(75, 54)], fill=c); d.ellipse(box(24, 38, 76, 92), fill=c)
    elif n == "video":
        d.rounded_rectangle(box(4, 18, 96, 82), radius=10 * u * s, outline=c, width=lw)
        d.polygon([Pt(40, 34), Pt(40, 66), Pt(66, 50)], fill=c)
    elif n == "bolt":
        d.polygon([Pt(58, 2), Pt(18, 56), Pt(46, 56), Pt(36, 98), Pt(82, 40), Pt(54, 40), Pt(64, 2)], fill=c)
    elif n == "house":
        line((8, 46), (50, 8), (92, 46)); line((18, 38), (18, 94), (82, 94), (82, 38))
    elif n == "alert":
        d.polygon([Pt(50, 6), Pt(96, 90), Pt(4, 90)], fill=c)
        d.rectangle(box(46, 34, 54, 64), fill=bg); d.rectangle(box(46, 72, 54, 80), fill=bg)
    elif n == "user":
        d.ellipse(box(30, 8, 70, 48), fill=c); d.pieslice(box(12, 54, 88, 130), 180, 360, fill=c)
    elif n == "cloud":
        d.ellipse(box(8, 40, 48, 80), fill=c); d.ellipse(box(28, 20, 76, 68), fill=c)
        d.ellipse(box(56, 38, 94, 80), fill=c); d.rectangle(box(28, 58, 76, 80), fill=c)
    elif n == "eye":
        d.chord(box(4, 22, 96, 92), 200, 340, fill=c); d.chord(box(4, 8, 96, 78), 20, 160, fill=c)
        d.ellipse(box(36, 36, 64, 64), fill=bg); d.ellipse(box(43, 43, 57, 57), fill=c)
    elif n == "chart":
        line((8, 8), (8, 92), (92, 92)); line((20, 72), (42, 50), (60, 62), (90, 24), w=1.3)
    elif n == "mail":
        d.rounded_rectangle(box(6, 20, 94, 80), radius=8 * u * s, outline=c, width=lw); line((8, 24), (50, 56), (92, 24))
    elif n == "phone":
        d.rounded_rectangle(box(26, 4, 74, 96), radius=10 * u * s, outline=c, width=lw); line((44, 84), (56, 84))
    elif n == "bug":
        d.ellipse(box(28, 24, 72, 90), fill=c); d.ellipse(box(36, 8, 64, 34), fill=c)
        for y0 in (40, 56, 72): line((10, y0 - 6), (28, y0)); line((90, y0 - 6), (72, y0))
    elif n == "link":
        d.rounded_rectangle(box(6, 30, 56, 70), radius=20 * u * s, outline=c, width=lw)
        d.rounded_rectangle(box(44, 30, 94, 70), radius=20 * u * s, outline=c, width=lw)
    elif n == "search":
        d.ellipse(box(8, 8, 66, 66), outline=c, width=round(lw * 1.2)); line((58, 58), (92, 92), w=1.6)
    elif n == "check":
        line((12, 52), (38, 78), (90, 22), w=1.6)
    elif n == "cross":
        line((16, 16), (84, 84), w=1.6); line((84, 16), (16, 84), w=1.6)
    elif n == "wifi":
        for r_ in (44, 30, 16): d.arc(box(50 - r_, 70 - r_, 50 + r_, 70 + r_), 225, 315, fill=c, width=lw)
        d.ellipse(box(44, 74, 56, 86), fill=c)
    elif n == "money":
        d.rounded_rectangle(box(4, 22, 96, 78), radius=8 * u * s, outline=c, width=lw)
        d.ellipse(box(36, 34, 64, 66), outline=c, width=lw)


# ------------------------------------------------------------------ globe
def project_globe(lat, lon, c, R, cx, cy, tilt=math.radians(22)):
    p, l = math.radians(lat), math.radians(lon - c)
    x, y, z = math.cos(p) * math.sin(l), math.sin(p), math.cos(p) * math.cos(l)
    y, z = y * math.cos(tilt) - z * math.sin(tilt), y * math.sin(tilt) + z * math.cos(tilt)
    return cx + R * x, cy - R * y, z

_globe_base = {}
def globe_sprite(R, c, pins, t, labels=True):
    """Wireframe globe drawn at 2x. pins: (name, lat, lon, t_appear)."""
    S2, M = 2, 170
    size = (2 * R + 2 * M) * S2; cx = cy = size / 2; RR = R * S2
    if R not in _globe_base:
        disc = Image.new("L", (size, size), 0)
        ImageDraw.Draw(disc).ellipse((cx - RR * 1.25, cy - RR * 1.25, cx + RR * 1.25, cy + RR * 1.25), fill=255)
        _globe_base[R] = tint(disc.filter(ImageFilter.GaussianBlur(40 * S2)), P.night, 0.65)
    out = _globe_base[R].copy()
    back = Image.new("RGBA", (size, size), (0, 0, 0, 0)); front = back.copy(); top = back.copy()
    db, dfr, dt = ImageDraw.Draw(back), ImageDraw.Draw(front), ImageDraw.Draw(top)
    lines = [[(la, lo) for la in range(-90, 91, 5)] for lo in range(0, 360, 20)]
    lines += [[(la, lo) for lo in range(0, 361, 5)] for la in (-60, -40, -20, 20, 40, 60)]
    for pts in lines:
        pp = [project_globe(la, lo, c, RR, cx, cy) for la, lo in pts]
        for (x0, y0, z0), (x1, y1, z1) in zip(pp, pp[1:]):
            if z0 + z1 > 0: dfr.line((x0, y0, x1, y1), fill=hexrgb(P.cyan, 140), width=2 * S2)
            else: db.line((x0, y0, x1, y1), fill=hexrgb(P.cyan, 34), width=S2)
    eq = [project_globe(0, lo, c, RR, cx, cy) for lo in range(0, 361, 4)]
    for (x0, y0, z0), (x1, y1, z1) in zip(eq, eq[1:]):
        if z0 + z1 > 0: dfr.line((x0, y0, x1, y1), fill=hexrgb(P.violet, 220), width=3 * S2)
    dfr.ellipse((cx - RR, cy - RR, cx + RR, cy + RR), outline=hexrgb(P.cyan, 210), width=3 * S2)
    placed = []
    for name, la, lo, t0 in pins:
        if t < t0: continue
        x, y, z = project_globe(la, lo, c, RR, cx, cy)
        if z < 0.05: continue
        vis = min(1.0, (z - 0.05) / 0.25) * ease((t - t0) / 0.15)
        dt.ellipse((x - 10 * S2, y - 10 * S2, x + 10 * S2, y + 10 * S2), fill=hexrgb(P.red, int(255 * vis)),
                   outline=hexrgb(P.white, int(230 * vis)), width=2 * S2)
        for k in range(2):
            p = ((t - t0) / 1.3 + k * 0.5) % 1.0
            if t - t0 < k * 0.65: continue
            rr = (14 + 60 * p) * S2
            dt.ellipse((x - rr, y - rr, x + rr, y + rr), outline=hexrgb(P.red, int(220 * (1 - p) * vis)), width=3 * S2)
        if labels and name:
            f = font(F_MONO, 22); lw_ = f.getlength(name.upper())
            lx, ly = x + 20 * S2, y - 46 * S2
            if any(abs(ly - py) < 44 * S2 and abs(lx - px) < 260 * S2 for px, py in placed): ly = y + 14 * S2
            placed.append((lx, ly))
            dt.rounded_rectangle((lx, ly, lx + lw_ + 28 * S2, ly + 40 * S2), radius=20 * S2,
                                 fill=hexrgb(P.night, int(225 * vis)))
            dt.text((lx + 14 * S2, ly + 20 * S2), name.upper(), font=f, fill=hexrgb(P.white, int(255 * vis)), anchor="lm")
    out.alpha_composite(back); out.alpha_composite(front.filter(ImageFilter.GaussianBlur(7 * S2)))
    out.alpha_composite(front); out.alpha_composite(top)
    return out.resize((size // S2, size // S2), Image.LANCZOS)


# ------------------------------------------------------------------ shared sprites
def callout(icon_name, kicker, main, col=None, w=900):
    col = colour(col or "red")
    lines = wrap(F_TITLE, 46, main, w - 190)
    h = 104 + 56 * len(lines)
    def fn(d, s, im):
        panel(d, s, 0, 0, w, h, r=30, border=col, ba=120)
        d.ellipse((26 * s, (h / 2 - 48) * s, 122 * s, (h / 2 + 48) * s), fill=hexrgb(col, 45), outline=hexrgb(col), width=2 * s)
        icon(d, s, icon_name, 46, h / 2 - 28, 56, col)
        txt(d, s, 148, 30, kicker, F_MONO, 26, col)
        for i, ln in enumerate(lines): txt(d, s, 148, 66 + i * 56, ln, F_TITLE, 46, P.white)
    return sprite(w, h, fn)

def pill(text, fill, fg=None, px=28, path=None, h=58, icon_name=None):
    path = path or F_MONO
    w = tw(path, px, text) + (86 if icon_name else 50)
    def fn(d, s, im):
        panel(d, s, 0, 0, w, h, r=h / 2, fill=fill, a=255)
        x = 25
        if icon_name: icon(d, s, icon_name, 20, h / 2 - 14, 28, fg or P.white); x = 60
        txt(d, s, x, h / 2, text, path, px, fg or P.white, "lm")
    return sprite(w, h, fn)
