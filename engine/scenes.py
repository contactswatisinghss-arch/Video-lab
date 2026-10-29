"""Scene templates. Each takes (ctx, spec) where every time in spec is a second on the RAW video.
docs/scenes.md describes every field; keep the two in step."""
import math, random
from PIL import Image, ImageDraw, ImageFilter
from .common import *

SCENES = {}
def scene(fn): SCENES[fn.__name__] = fn; return fn

def _callouts(frame, t, lt, items, y=830, cache={}):
    for c in items or []:
        key = (c.get("icon", "alert"), c.get("kicker", ""), c.get("text", ""), c.get("color", "red"))
        if key not in cache: cache[key] = callout(*key)
        k = window(t, lt(c["start"]), lt(c["end"]))
        if k > 0: paste(frame, cache[key], 540, c.get("y", y) + 25 * (1 - appear(t, lt(c["start"]))), k)


# ================================================================ hook
@scene
def hook_globe(ctx, sp):
    """Glitch-in title over a turning wireframe globe with red pings."""
    a, b = sp["start"], sp["end"]
    title = sp.get("title", [["BREAKING", "white"], ["NEWS", "red"]])
    kicker = sp.get("kicker", "")
    pings = sp.get("pings", [])
    t_out_raw = sp.get("title_out", b - 2.4)
    lon0 = sp.get("lon_start", (pings[0]["lon"] - 15) if pings else 0)
    spin = sp.get("spin", 24)
    W_, H_, S = 1080, 900, 2
    CX, CY, R = 540 * S, 500 * S, 225 * S
    big = font(F_TITLE, 150 / 2 * S)  # font() already doubles; 150px at 2x canvas
    kick = font(F_MONO, 30 / 2 * S)
    asc, desc = big.getmetrics(); lh = int(asc * 0.98)
    tw_ = int(max(big.getlength(t_[0]) for t_ in title))
    timg = Image.new("RGBA", (tw_ + 80 * S, lh * len(title) + desc + 50 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(timg)
    for i, (txt_, col) in enumerate(title):
        d.text(((timg.width - big.getlength(txt_)) / 2, 25 * S + i * lh), txt_, font=big, fill=hexrgb(col))
    tmask = timg.getchannel("A")
    tshadow = tint(tmask.filter(ImageFilter.GaussianBlur(18 * S)), P.night, 0.9)
    tx, ty = CX - timg.width // 2, CY - timg.height // 2 - 20 * S
    kx = CX - kick.getlength(kicker) / 2
    halo = Image.new("L", (W_ * S, H_ * S), 0)
    ImageDraw.Draw(halo).ellipse((CX - R * 1.5, CY - R * 1.5, CX + R * 1.5, CY + R * 1.5), fill=255)
    halo = tint(halo.filter(ImageFilter.GaussianBlur(70 * S)), P.night, 1.0)
    disc = Image.new("L", (W_ * S, H_ * S), 0)
    ImageDraw.Draw(disc).ellipse((CX - R, CY - R, CX + R, CY + R), fill=255)
    disc = tint(disc, P.night, 1.0)

    def draw(frame_out, t, lt, dur):
        T_OUT = lt(t_out_raw)
        rnd = random.Random(int(t * 30))
        c = lon0 + spin * t
        ga = ease(t / 0.45) * (1 - 0.45 * ease((t - T_OUT) / 0.35))
        frame = Image.new("RGBA", (W_ * S, H_ * S), (0, 0, 0, 0))
        frame.alpha_composite(fade_img(halo, 0.55 * ga)); frame.alpha_composite(fade_img(disc, 0.35 * ga))
        back = Image.new("RGBA", frame.size, (0, 0, 0, 0)); front = back.copy()
        db, dfr = ImageDraw.Draw(back), ImageDraw.Draw(front)
        lines = [[(la, lo) for la in range(-90, 91, 4)] for lo in range(0, 360, 20)]
        lines += [[(la, lo) for lo in range(0, 361, 4)] for la in (-60, -40, -20, 20, 40, 60)]
        for pts in lines:
            pp = [project_globe(la, lo, c, R, CX, CY) for la, lo in pts]
            for (x0, y0, z0), (x1, y1, z1) in zip(pp, pp[1:]):
                if z0 + z1 > 0: dfr.line((x0, y0, x1, y1), fill=hexrgb(P.cyan, 150), width=2 * S)
                else: db.line((x0, y0, x1, y1), fill=hexrgb(P.cyan, 38), width=S)
        eq = [project_globe(0, lo, c, R, CX, CY) for lo in range(0, 361, 3)]
        for (x0, y0, z0), (x1, y1, z1) in zip(eq, eq[1:]):
            if z0 + z1 > 0: dfr.line((x0, y0, x1, y1), fill=hexrgb(P.violet, 230), width=3 * S)
            else: db.line((x0, y0, x1, y1), fill=hexrgb(P.violet, 60), width=S)
        dfr.ellipse((CX - R, CY - R, CX + R, CY + R), outline=hexrgb(P.cyan, 220), width=3 * S)
        for pg in pings:
            t0 = lt(pg["at"])
            if t < t0: continue
            x, y, z = project_globe(pg["lat"], pg["lon"], c, R, CX, CY)
            if z < 0.05: continue
            vis = min(1.0, (z - 0.05) / 0.25) * ease((t - t0) / 0.12)
            dfr.ellipse((x - 9 * S, y - 9 * S, x + 9 * S, y + 9 * S), fill=hexrgb(P.red, int(255 * vis)))
            for k in range(2):
                p = ((t - t0) / 1.2 + k * 0.5) % 1.0
                if t - t0 < k * 0.6: continue
                rr = (12 + 58 * p) * S
                dfr.ellipse((x - rr, y - rr, x + rr, y + rr), outline=hexrgb(P.red, int(230 * (1 - p) * vis)), width=3 * S)
        globe = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        globe.alpha_composite(back); globe.alpha_composite(front.filter(ImageFilter.GaussianBlur(8 * S)))
        globe.alpha_composite(front)
        frame.alpha_composite(fade_img(globe, ga))
        if 0.08 <= t < T_OUT:
            g = 0.0
            if t < 0.6: g = 1 - (t - 0.08) / 0.52
            elif 1.9 <= t < 2.0: g = 0.35
            elif t > T_OUT - 0.22: g = (t - (T_OUT - 0.22)) / 0.22
            if not (g > 0.5 and rnd.random() < 0.25):
                frame.alpha_composite(tshadow, (tx, ty))
                if g > 0.02:
                    split = int(16 * S * g)
                    frame.alpha_composite(tint(tmask, P.cyan, 0.7), (tx - split, ty))
                    frame.alpha_composite(tint(tmask, P.red, 0.7), (tx + split, ty))
                    y0 = 0
                    while y0 < timg.height:
                        bh = rnd.randint(6, 26) * S
                        dx = int(rnd.uniform(-1, 1) * 70 * S * g) if rnd.random() < 0.6 else 0
                        frame.alpha_composite(timg.crop((0, y0, timg.width, min(y0 + bh, timg.height))), (tx + dx, ty + y0))
                        y0 += bh
                else:
                    frame.alpha_composite(timg, (tx, ty))
                ka = ease((t - 0.7) / 0.3) * (1 - ease((t - (T_OUT - 0.22)) / 0.15))
                if ka > 0 and kicker:
                    ky, kw = ty + timg.height + 6 * S, kick.getlength(kicker)
                    dk = ImageDraw.Draw(frame)
                    dk.rounded_rectangle((kx - 18 * S, ky - 4 * S, kx + kw + 18 * S, ky + 42 * S), radius=22 * S,
                                         fill=hexrgb(P.night, int(215 * ka)))
                    dk.text((kx, ky), kicker, font=kick, fill=hexrgb(P.cyan, int(255 * ka)))
        frame_out.alpha_composite(frame.resize((W_, H_), Image.LANCZOS))
    ctx.run_layer("hook_globe", a, b, draw, H=900, edge=0.3, fade_in=False)


@scene
def hook_title(ctx, sp):
    """Big stacked title that glitches in, no globe (use when there is no 'where' angle)."""
    sp = dict(sp); sp.setdefault("pings", [])
    a, b = sp["start"], sp["end"]
    title = sp.get("title", [["BIG", "white"], ["NEWS", "red"]])
    kicker = sp.get("kicker", "")
    def mk(d, s, im):
        for i, (txt_, col) in enumerate(title): txt(d, s, 450, 90 + i * 150, txt_, F_TITLE, 150, col, "mm")
    timg = with_shadow(sprite(900, 150 * len(title) + 40, mk), 18, 0.9, 0)
    kick = pill(kicker, P.night, P.cyan, 30) if kicker else None
    def draw(frame, t, lt, dur):
        g = 1 - ease((t - 0.08) / 0.5)
        if t < 0.08: return
        rnd = random.Random(int(t * 30))
        y = 470
        if g > 0.02:
            m = timg.getchannel("A")
            sx = int(16 * g)
            frame.alpha_composite(tint(m, P.cyan, 0.7), (540 - timg.width // 2 - sx, y - timg.height // 2))
            frame.alpha_composite(tint(m, P.red, 0.7), (540 - timg.width // 2 + sx, y - timg.height // 2))
            y0 = 0
            while y0 < timg.height:
                bh = rnd.randint(6, 26); dx = int(rnd.uniform(-1, 1) * 70 * g)
                frame.alpha_composite(timg.crop((0, y0, timg.width, min(timg.height, y0 + bh))),
                                      (540 - timg.width // 2 + dx, y - timg.height // 2 + y0)); y0 += bh
        else:
            paste(frame, timg, 540, y)
        if kick: paste(frame, kick, 540, y + timg.height / 2 + 10, appear(t, 0.7))
    ctx.run_layer("hook_title", a, b, draw)


# ================================================================ data
@scene
def stat_meter(ctx, sp):
    """Tilted stat sticker that counts up, plus an optional severity meter."""
    a, b = sp["start"], sp["end"]
    st = sp.get("sticker", {}); me = sp.get("meter")
    value, suffix, label = st.get("value", 70), st.get("suffix", "%"), st.get("label", "")
    col = colour(st.get("color", "red"))
    cache = {}
    def sticker(v):
        w, h = 600, 330
        def fn(d, s, im):
            d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=44 * s, fill=hexrgb(P.white))
            d.rounded_rectangle((10 * s, 10 * s, (w - 10) * s, (h - 10) * s), radius=36 * s, fill=hexrgb(col))
            txt(d, s, w / 2, 130, f"{v}{suffix}", F_TITLE, 190, P.white, "mm")
            txt(d, s, w / 2, h - 58, label, F_MONO, 30, P.white, "mm")
        im = sprite(w, h, fn).rotate(5, resample=Image.BICUBIC, expand=True)
        return with_shadow(im, 14, 0.7, 10)
    def meter(v):
        w, h = 860, 168; mx = me.get("max", 10)
        def fn(d, s, im):
            panel(d, s, 0, 0, w, h, r=28, border=P.red, ba=140)
            txt(d, s, 34, 26, me.get("label", "SEVERITY"), F_MONO, 30, P.cyan)
            tail = f" / {mx:g}"; tw2 = tw(F_MONO, 30, tail)
            txt(d, s, w - 34 - tw2, 52, f"{v:.1f}", F_TITLE, 64, P.red, "rm")
            txt(d, s, w - 34 - tw2, 44, tail, F_MONO, 30, P.white, "la", 170)
            x0, y0, sw, gap, sh = 34, 96, 72, 8, 40
            for i in range(10):
                sx = x0 + i * (sw + gap)
                d.rounded_rectangle((sx * s, y0 * s, (sx + sw) * s, (y0 + sh) * s), radius=8 * s, fill=hexrgb(P.white, 28))
                part = min(max(v / mx * 10 - i, 0), 1)
                if part > 0:
                    c2 = P.red if i >= 6 else ("#FF8A3D" if i >= 3 else P.amber)
                    d.rounded_rectangle((sx * s, y0 * s, (sx + sw * part) * s, (y0 + sh) * s), radius=8 * s, fill=hexrgb(c2))
            tag = me.get("tag")
            if tag and v >= me.get("value", mx) - 0.001:
                lx = 34 + tw(F_MONO, 30, me.get("label", "SEVERITY")) + 20
                panel(d, s, lx, 24, lx + tw(F_MONO, 24, tag) + 24, 62, r=19, fill=P.red, a=255)
                txt(d, s, lx + 12, 43, tag, F_MONO, 24, P.white, "lm")
        return with_shadow(sprite(w, h, fn), 12, 0.5, 8)
    def draw(frame, t, lt, dur):
        t0 = lt(st.get("at", a))
        if t < t0: return
        k = (t - t0) / 0.35
        v = int(round(value * ease((t - t0) / 0.8))) if st.get("count_up", True) and isinstance(value, int) else value
        if v not in cache: cache[v] = sticker(v)
        paste(frame, cache[v], 540, 470, min(1, k * 3), 1.35 - 0.35 * spring(k))
        if me:
            tm = lt(me.get("at", a + 0.55))
            if t >= tm:
                km = (t - tm) / 0.3
                vv = me["value"] * ease((t - tm - 0.15) / 0.9)
                paste(frame, meter(round(vv, 1)), 540, 790 - 30 * (1 - ease(km)), ease(km))
    ctx.run_layer("stat_meter", a, b, draw)


@scene
def news_cards(ctx, sp):
    """Label pill + stacked paper news cards dropping in. Recreated cards, never screenshots or logos."""
    a, b = sp["start"], sp["end"]
    lab = sp.get("label")
    def card(outlet, date, head, rot):
        w, pad = 900, 34
        lines = wrap(F_SERIF, 46, head, w - 2 * pad - 14)
        h = pad + 40 + len(lines) * 56 + pad
        def fn(d, s, im):
            d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=18 * s, fill=hexrgb(P.paper))
            d.rectangle((0, 22 * s, 7 * s, (h - 22) * s), fill=hexrgb(P.red))
            icon(d, s, "alert", pad + 12, pad - 4, 28, P.red)
            txt(d, s, pad + 54, pad - 4, outlet.upper(), F_MONO, 24, P.night, "la", 200)
            txt(d, s, w - pad, pad - 4, date, F_MONO, 24, P.night, "ra", 140)
            for i, ln in enumerate(lines): txt(d, s, pad + 14, pad + 36 + i * 56, ln, F_SERIF, 46, P.night)
        return with_shadow(sprite(w, h, fn).rotate(rot, resample=Image.BICUBIC, expand=True), 16, 0.65, 12)
    rots = (-1.6, 1.1, -0.8, 1.4)
    cards = [card(c.get("outlet", ""), c.get("date", ""), c.get("headline", ""), rots[i % 4])
             for i, c in enumerate(sp.get("cards", []))]
    label = pill(lab["text"], colour(lab.get("color", "red")), P.white, 30) if lab else None
    step = sp.get("step", 0.28)
    def draw(frame, t, lt, dur):
        t0 = lt(sp.get("at", a))
        if t < t0: return
        y = 362
        if label:
            kl = ease((t - t0) / 0.25); paste(frame, label, 540, 300 - 20 * (1 - kl), kl)
        else: y = 300
        for i, c in enumerate(cards):
            kc = (t - t0 - 0.12 - i * step) / 0.4
            if kc > 0: paste(frame, c, 540, y + c.height / 2 - 30 - 70 * (1 - spring(kc)), min(1, kc * 2.5))
            y += c.height - 120
    ctx.run_layer("news_cards", a, b, draw)


@scene
def callout_card(ctx, sp):
    """One icon card (kicker + text). Good for a single fact."""
    sp2 = dict(sp)
    def draw(frame, t, lt, dur):
        _callouts(frame, t, lt, [{**sp2, "start": sp2["start"], "end": sp2["end"]}], y=sp2.get("y", 330))
    ctx.run_layer("callout", sp["start"], sp["end"], draw, edge=0.01)


# ================================================================ place
@scene
def globe_pins(ctx, sp):
    """Globe turns to each pin as it is mentioned; callout cards underneath."""
    a, b = sp["start"], sp["end"]
    pins = sorted(sp.get("pins", []), key=lambda p: p["at"])
    turns = sp.get("turns")
    if not turns:
        turns = [[a, (pins[0]["lon"] - 10) if pins else 0]]
        for p in pins:
            turns += [[max(p["at"] - 0.7, turns[-1][0]), turns[-1][1]], [p["at"] + 0.1, p["lon"] - 10]]
    def draw(frame, t, lt, dur):
        kf = [(lt(x), lo) for x, lo in turns]
        c = kf[-1][1]
        if t <= kf[0][0]: c = kf[0][1]
        for (ta, la), (tb, lb) in zip(kf, kf[1:]):
            if ta <= t <= tb: c = la + (lb - la) * ease((t - ta) / max(tb - ta, 1e-3)); break
        g = globe_sprite(200, c, [(p.get("name", ""), p["lat"], p["lon"], lt(p["at"])) for p in pins], t)
        paste(frame, g, 540, 480)
        _callouts(frame, t, lt, sp.get("callouts"), y=815)
    ctx.run_layer("globe_pins", a, b, draw)


# ================================================================ explain
@scene
def title_chip(ctx, sp):
    """Mono name chip, a subtitle, and red tag pills (e.g. CVE numbers)."""
    a, b = sp["start"], sp["end"]
    title = sp.get("title", "")
    cw = max(420, tw(F_MONO, 92, title) + 100)
    chip = sprite(cw, 150, lambda d, s, im: (panel(d, s, 0, 0, cw, 150, r=30, border=P.cyan, ba=200, bw=3),
                                             txt(d, s, cw / 2, 75, title, F_MONO, 92, P.white, "mm")))
    sub = sprite(900, 70, lambda d, s, im: txt(d, s, 450, 35, sp.get("subtitle", ""), F_TITLE, 46, P.white, "mm"))
    tags = [pill(x, P.red, P.white, 28, icon_name="alert") for x in sp.get("tags", [])]
    def draw(frame, t, lt, dur):
        paste(frame, chip, 540, 380, appear(t, 0, 0.2), 1.25 - 0.25 * spring(t / 0.5))
        paste(frame, sub, 540, 515, appear(t, 0.4))
        n = len(tags); gap = 20; total = sum(tg.width for tg in tags) + gap * (n - 1)
        x = 540 - total / 2
        for i, tg in enumerate(tags):
            k = appear(t, 1.0 + i * 0.35)
            if total > 1000: paste(frame, tg, 540, 610 + i * 72 - 25 * (1 - k), k)
            else: paste(frame, tg, x + tg.width / 2, 610 - 25 * (1 - k), k)
            x += tg.width + gap
    ctx.run_layer("title_chip", a, b, draw)


@scene
def stack(ctx, sp):
    """Layer diagram (top to bottom) with an optional crack in one layer and callouts below."""
    a, b = sp["start"], sp["end"]
    layers = sp.get("layers", [])
    cr = sp.get("crack"); all_red = sp.get("all_red_at")
    def slab(l, red):
        w, h = 800, 124
        fill = colour(l.get("fill", "night"))
        border = P.red if red else (fill if l.get("fill") not in (None, "night") else P.cyan)
        def fn(d, s, im):
            panel(d, s, 0, 0, w, h, r=24, fill=fill, a=230, border=border, ba=230, bw=3)
            icon(d, s, l.get("icon", "browser"), 34, 30, 64, P.white)
            txt(d, s, 128, 62, l.get("label", ""), F_TITLE, 50, P.white, "lm")
            txt(d, s, w - 34, 62, l.get("note", ""), F_MONO, 24, P.white, "rm", 170)
        return sprite(w, h, fn)
    sl = [slab(l, False) for l in layers]; slr = [slab(l, True) for l in layers]
    n = len(layers); gap = 160 if n <= 3 else 140
    YS = [330 + i * gap for i in range(n)]
    conn = sprite(40, 40, lambda d, s, im: (d.line((20 * s, 0, 20 * s, 26 * s), fill=hexrgb(P.cyan), width=3 * s),
                                           d.polygon([(10 * s, 22 * s), (30 * s, 22 * s), (20 * s, 38 * s)], fill=hexrgb(P.cyan))))
    rnd = random.Random(7); pts = [(40, -62)]
    for i in range(1, 9): pts.append((40 + rnd.uniform(-22, 22), -62 + i * 15.5))
    flaw = pill(cr.get("tag", "FLAW") if cr else "FLAW", P.red, P.white, 26)
    def draw(frame, t, lt, dur):
        crack_t = lt(cr["at"]) if cr else 1e9
        all_t = lt(all_red) if all_red else 1e9
        ci = cr.get("layer", 1) if cr else -1
        for i, y in enumerate(YS):
            k = appear(t, i * 0.3, 0.35)
            red = (i == ci and t >= crack_t) or t >= all_t
            paste(frame, slr[i] if red else sl[i], 540, y - 40 * (1 - spring((t - i * 0.3) / 0.6)), k)
            if i < n - 1 and k > 0.9: paste(frame, conn, 540, y + gap / 2 + 2, k)
        if t >= all_t:
            p = 0.5 + 0.5 * math.sin((t - all_t) * 6)
            hh = YS[-1] - YS[0] + 200
            glow = Image.new("L", (900, hh), 0)
            ImageDraw.Draw(glow).rounded_rectangle((40, 40, 860, hh - 40), radius=30, outline=255, width=14)
            frame.alpha_composite(tint(glow.filter(ImageFilter.GaussianBlur(14)), P.red, 0.35 + 0.35 * p), (90, YS[0] - 100))
        if t >= crack_t:
            k = ease((t - crack_t) / 0.5); m = max(2, int(len(pts) * k) + 1); seg = pts[:m]
            y = YS[ci]
            lay = Image.new("RGBA", (1080, 180), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
            dl.line([(540 + x, 90 + yy) for x, yy in seg], fill=hexrgb(P.red), width=7, joint="curve")
            frame.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6)), (0, y - 90)); frame.alpha_composite(lay, (0, y - 90))
            ImageDraw.Draw(frame).line([(540 + x, y + yy) for x, yy in seg], fill=hexrgb(P.white, 200), width=2)
            paste(frame, flaw, 860, y - 62, appear(t, crack_t + 0.4), 1.3 - 0.3 * spring((t - crack_t - 0.4) / 0.4))
        _callouts(frame, t, lt, sp.get("callouts"), y=YS[-1] + 180)
    ctx.run_layer("stack", a, b, draw)


@scene
def login_breach(ctx, sp):
    """Frosted sign-in box, fields struck out, a stamp, then impact rows tick on."""
    a, b = sp["start"], sp["end"]
    W_, H_ = 700, 470
    fields = sp.get("fields", ["Username", "Password"])
    def box_fn(d, s, im):
        panel(d, s, 0, 0, W_, H_, r=34, a=160, border=P.white, ba=80)
        panel(d, s, 2, 2, W_ - 2, H_ - 2, r=32, fill=P.white, a=26)
        icon(d, s, "lock", 40, 34, 44, P.cyan); txt(d, s, 100, 56, sp.get("title", "Sign in"), F_TITLE, 44, P.white, "lm")
        for i, ph in enumerate(fields[:2]):
            y = 120 + i * 108
            panel(d, s, 40, y, W_ - 40, y + 80, r=18, fill=P.white, a=22, border=P.white, ba=70)
            txt(d, s, 68, y + 40, ph if i == 0 else "••••••••", F_TITLE, 32, P.white, "lm", 150)
        panel(d, s, 40, 352, W_ - 40, 432, r=18, fill=P.cyan, a=255)
        txt(d, s, W_ / 2, 392, sp.get("button", "LOG IN"), F_MONO, 32, P.night, "mm")
    box = sprite(W_, H_, box_fn)
    tag = pill(sp.get("tag", "NOT NEEDED"), P.red, P.white, 24, h=46)
    stamp_txt = sp.get("stamp", {}).get("text", ["ACCESS", "GRANTED"])
    def stamp_fn(d, s, im):
        d.rounded_rectangle((6 * s, 6 * s, 594 * s, 184 * s), radius=16 * s, outline=hexrgb(P.red), width=8 * s)
        d.rounded_rectangle((22 * s, 22 * s, 578 * s, 168 * s), radius=10 * s, outline=hexrgb(P.red), width=3 * s)
        for i, ln in enumerate(stamp_txt[:2]): txt(d, s, 300, 70 + i * 58 if len(stamp_txt) > 1 else 95, ln, F_TITLE, 62, P.red, "mm")
    stamp = sprite(600, 190, stamp_fn).rotate(-11, resample=Image.BICUBIC, expand=True)
    def row(icon_name, label):
        w, h = 780, 88
        def fn(d, s, im):
            panel(d, s, 0, 0, w, h, r=24, border=P.red, ba=90)
            d.ellipse((14 * s, 12 * s, 78 * s, 76 * s), fill=hexrgb(P.red)); icon(d, s, icon_name, 28, 26, 36, P.white)
            txt(d, s, 100, 44, label, F_TITLE, 42, P.white, "lm")
        return sprite(w, h, fn)
    rows = [(it["at"], row(it.get("icon", "alert"), it["text"])) for it in sp.get("items", [])]
    strikes = {}
    def strike(frac):
        w = max(8, 560 * frac)
        return sprite(w + 20, 20, lambda d, s, im: d.rounded_rectangle((10 * s, 4 * s, (10 + w) * s, 14 * s), radius=5 * s, fill=hexrgb(P.red)))
    def draw(frame, t, lt, dur):
        k_up = ease((t - lt(sp["list_at"])) / 0.5) if rows and "list_at" in sp else 0
        sc = 1 - 0.38 * k_up; cy = 520 - 115 * k_up
        bx = box.copy()
        for i in range(min(2, len(fields))):
            t0 = lt(sp.get("strike_at", a + 0.6)) + i * 0.7; k = ease((t - t0) / 0.35)
            if k > 0:
                q = round(k * 20) / 20
                if q not in strikes: strikes[q] = strike(q)
                bx.alpha_composite(strikes[q], (60, 120 + i * 108 + 30))
                kn = appear(t, t0 + 0.35, 0.2)
                if kn > 0: bx.alpha_composite(fade_img(tag, kn), (W_ - 40 - tag.width - 16, 120 + i * 108 + 17))
        paste(frame, bx, 540, cy, 1.0, sc)
        if "stamp" in sp:
            ks = (t - lt(sp["stamp"]["at"])) / 0.4
            if ks > 0: paste(frame, stamp, 540, cy + 20 * sc, min(1, ks * 3) * 0.95, (1.8 - 0.8 * spring(ks)) * sc)
        for i, (at, rw) in enumerate(rows):
            k = (t - lt(at)) / 0.4
            if k > 0: paste(frame, rw, 540 + 60 * (1 - ease(k)), 600 + i * 104, ease(min(1, k * 1.5)), 0.92 + 0.08 * spring(k))
    ctx.run_layer("login_breach", a, b, draw)


@scene
def icon_list(ctx, sp):
    """A titled list where each row (icon + text) ticks on when spoken."""
    a, b = sp["start"], sp["end"]
    col = colour(sp.get("color", "cyan"))
    head = pill(sp["title"], P.night, col, 30) if sp.get("title") else None
    def row(icon_name, label):
        w, h = 860, 92
        def fn(d, s, im):
            panel(d, s, 0, 0, w, h, r=24, border=col, ba=100)
            d.ellipse((14 * s, 12 * s, 82 * s, 80 * s), fill=hexrgb(col)); icon(d, s, icon_name, 29, 27, 38, P.night)
            txt(d, s, 104, 46, label, F_TITLE, 40, P.white, "lm")
        return sprite(w, h, fn)
    rows = [(it["at"], row(it.get("icon", "check"), it["text"])) for it in sp.get("items", [])]
    def draw(frame, t, lt, dur):
        y0 = 300
        if head: paste(frame, head, 540, y0, appear(t, 0)); y0 += 80
        for i, (at, rw) in enumerate(rows):
            k = (t - lt(at)) / 0.4
            if k > 0: paste(frame, rw, 540 + 60 * (1 - ease(k)), y0 + i * 106, ease(min(1, k * 1.5)), 0.92 + 0.08 * spring(k))
    ctx.run_layer("icon_list", a, b, draw)


@scene
def hero_row(ctx, sp):
    """Analogy: one hero icon (e.g. key) glides in, then a row of items (e.g. houses) open one by one."""
    a, b = sp["start"], sp["end"]
    n = sp.get("count", 5)
    label = sprite(900, 110, lambda d, s, im: (panel(d, s, 0, 0, 900, 110, r=30),
                                               txt(d, s, 450, 55, sp.get("label", ""), F_TITLE, 42, P.white, "mm")))
    item = sp.get("item_icon", "house")
    def thing(open_):
        def fn(d, s, im):
            if item == "house":
                d.rectangle((58 * s, 92 * s, 92 * s, 148 * s), fill=hexrgb(P.red if open_ else P.violet, 230 if open_ else 255))
                if open_: d.polygon([(58 * s, 92 * s), (44 * s, 100 * s), (44 * s, 156 * s), (58 * s, 148 * s)], fill=hexrgb(P.white, 200))
                icon(d, s, "house", 0, 0, 150, P.cyan)
            else:
                icon(d, s, item, 15, 15, 120, P.red if open_ else P.cyan)
        return sprite(150, 150, fn)
    closed, opened = thing(False), thing(True)
    glow = Image.new("L", (240, 240), 0); ImageDraw.Draw(glow).ellipse((60, 60, 180, 180), fill=255)
    glow = tint(glow.filter(ImageFilter.GaussianBlur(30)), P.red, 0.7)
    hero = sprite(220, 220, lambda d, s, im: icon(d, s, sp.get("hero_icon", "key"), 10, 10, 200, P.amber))
    hglow = tint(hero.getchannel("A").filter(ImageFilter.GaussianBlur(14)), P.amber, 0.6)
    XS = [540 + (i - (n - 1) / 2) * min(200, 960 / n) for i in range(n)]
    def draw(frame, t, lt, dur):
        paste(frame, label, 540, 300 + 20 * (1 - appear(t, 0)), appear(t, 0))
        kx = -120 + 660 * ease((t - lt(sp.get("hero_at", a + 0.5))) / 1.0); bob = 8 * math.sin(t * 3)
        paste(frame, hglow, kx, 470 + bob); paste(frame, hero, kx, 470 + bob)
        for i, x in enumerate(XS):
            t_open = lt(sp.get("open_at", a + 1.7)) + i * sp.get("step", 0.32)
            k_in = appear(t, 0.1 + i * 0.08)
            if t >= t_open:
                paste(frame, glow, x, 700, appear(t, t_open, 0.3))
                paste(frame, opened, x, 680, k_in, 1 + 0.08 * (1 - spring((t - t_open) / 0.4)))
            else: paste(frame, closed, x, 680, k_in)
    ctx.run_layer("hero_row", a, b, draw)


@scene
def timeline(ctx, sp):
    """Vertical dated timeline; steps light up as spoken; line turns red from alert_at."""
    a, b = sp["start"], sp["end"]
    items = sp.get("items", [])
    LX, Y0 = 110, 390
    STEP = min(88, int(560 / max(1, len(items) - 1))) if len(items) > 1 else 88
    header = pill(sp.get("header", "HOW IT UNFOLDED"), P.night, P.cyan, 30, h=60)
    def node(icon_name, col):
        return sprite(70, 70, lambda d, s, im: (d.ellipse((3 * s, 3 * s, 67 * s, 67 * s), fill=hexrgb(P.night), outline=hexrgb(col), width=3 * s),
                                                icon(d, s, icon_name, 18, 18, 34, col)))
    def tpill(date, text, col):
        w = tw(F_MONO, 28, date) + tw(F_TITLE, 38, text) + 80
        return sprite(w, 66, lambda d, s, im: (panel(d, s, 0, 0, w, 66, r=20), txt(d, s, 22, 33, date, F_MONO, 28, col, "lm"),
                                               txt(d, s, 22 + tw(F_MONO, 28, date) + 26, 33, text, F_TITLE, 38, P.white, "lm")))
    nodes = [node(i.get("icon", "calendar"), colour(i.get("color", "white"))) for i in items]
    nodes_red = [node(i.get("icon", "calendar"), P.red) for i in items]
    pills = [tpill(i.get("date", ""), i.get("text", ""), colour(i.get("color", "white"))) for i in items]
    alert_at = sp.get("alert_at"); ai = sp.get("alert_index")
    def draw(frame, t, lt, dur):
        paste(frame, header, LX - 40 + header.width / 2, 310, appear(t, 0))
        red = ease((t - lt(alert_at)) / 0.5) if alert_at is not None else 0
        active = [i for i, it in enumerate(items) if t >= lt(it["at"])]
        d = ImageDraw.Draw(frame)
        if active:
            last = active[-1]; kg = ease((t - lt(items[last]["at"])) / 0.35)
            y_end = Y0 + (last - 1 + kg) * STEP if last > 0 else Y0
            col = tuple(int(x + (y - x) * red) for x, y in zip(hexrgb(P.cyan)[:3], hexrgb(P.red)[:3]))
            if y_end > Y0: d.rounded_rectangle((LX - 3, Y0, LX + 3, y_end), radius=3, fill=col + (255,))
        for i in active:
            k = appear(t, lt(items[i]["at"]), 0.35); y = Y0 + i * STEP
            if ai is not None and i == ai:
                for r_ in range(2):
                    p = ((t - lt(items[i]["at"])) / 1.1 + r_ * 0.5) % 1; rr = 36 + 50 * p
                    d.ellipse((LX - rr, y - rr, LX + rr, y + rr), outline=hexrgb(P.red, int(200 * (1 - p))), width=4)
            nd = nodes_red[i] if red > 0.5 else nodes[i]
            paste(frame, nd, LX, y, k, 0.6 + 0.4 * spring((t - lt(items[i]["at"])) / 0.4))
            paste(frame, pills[i], LX + 48 + pills[i].width / 2 - 30 * (1 - k), y, k)
    ctx.run_layer("timeline", a, b, draw)


# ================================================================ fix / action
@scene
def status_tiles(ctx, sp):
    """A title, then N tiles that flip to a status (e.g. servers going OFFLINE)."""
    a, b = sp["start"], sp["end"]
    n = sp.get("count", 3); ic = sp.get("icon", "server"); flip_label = sp.get("flip_label", "OFFLINE")
    fcol = colour(sp.get("flip_color", "red"))
    title = sprite(900, 150, lambda d, s, im: (panel(d, s, 0, 0, 900, 150, r=30),
                                               txt(d, s, 450, 58, sp.get("title", ""), F_TITLE, 48, P.white, "mm"),
                                               txt(d, s, 450, 112, sp.get("subtitle", ""), F_MONO, 28, fcol, "mm")))
    def tile(off):
        def fn(d, s, im):
            panel(d, s, 0, 0, 220, 230, r=26, border=fcol if off else P.cyan, ba=150)
            icon(d, s, ic, 50, 30, 120, P.grey if off else P.cyan)
            if off:
                panel(d, s, 30, 170, 190, 212, r=21, fill=fcol, a=255); txt(d, s, 110, 191, flip_label, F_MONO, 24, P.white, "mm")
            else: d.ellipse((98 * s, 178 * s, 122 * s, 202 * s), fill=hexrgb(P.green))
        return sprite(220, 230, fn)
    on, off = tile(False), tile(True)
    XS = [540 + (i - (n - 1) / 2) * 250 for i in range(n)]
    def draw(frame, t, lt, dur):
        paste(frame, title, 540, 330, appear(t, 0))
        for i, x in enumerate(XS):
            tf = lt(sp.get("flip_at", a + 1.0)) + i * sp.get("step", 0.6)
            o = t >= tf
            paste(frame, off if o else on, x, 600, appear(t, 0.2 + i * 0.1), 1 + 0.06 * (1 - spring((t - tf) / 0.4)) if o else 1)
    ctx.run_layer("status_tiles", a, b, draw)


@scene
def shield_versions(ctx, sp):
    """Green shield + big word (PATCHED) + version chips."""
    a, b = sp["start"], sp["end"]
    col = colour(sp.get("color", "green"))
    shield = sprite(240, 240, lambda d, s, im: icon(d, s, "shield_check", 10, 10, 220, col))
    sg = tint(shield.getchannel("A").filter(ImageFilter.GaussianBlur(24)), col, 0.6)
    word = sprite(900, 110, lambda d, s, im: txt(d, s, 450, 55, sp.get("title", "PATCHED"), F_TITLE, 96, col, "mm"))
    when = sprite(900, 44, lambda d, s, im: txt(d, s, 450, 22, sp.get("subtitle", ""), F_MONO, 26, P.white, "mm", 200))
    def chip(v):
        w = max(330, tw(F_MONO, 34, v) + 60)
        return sprite(w, 74, lambda d, s, im: (panel(d, s, 0, 0, w, 74, r=20, border=col, ba=230, bw=3), txt(d, s, w / 2, 37, v, F_MONO, 34, col, "mm")))
    chips = [chip(v) for v in sp.get("chips", [])]
    def draw(frame, t, lt, dur):
        ks = t / 0.5
        paste(frame, sg, 540, 420, appear(t, 0)); paste(frame, shield, 540, 420, min(1, ks * 3), 0.5 + 0.5 * spring(ks))
        paste(frame, word, 540, 600, appear(t, 0.3)); paste(frame, when, 540, 668, appear(t, 0.6))
        for i, cp in enumerate(chips):
            k = appear(t, 0.8 + i * 0.18)
            paste(frame, cp, 540 + (i % 2 - 0.5) * 350 if len(chips) > 1 else 540, 745 + (i // 2) * 88 + 20 * (1 - k), k)
    ctx.run_layer("shield_versions", a, b, draw)


@scene
def checklist(ctx, sp):
    """Action card: title, kicker, rows whose boxes tick green when spoken."""
    a, b = sp["start"], sp["end"]
    rows = sp.get("rows", [])
    col = colour(sp.get("color", "green"))
    hgt = 200 + 128 * len(rows) - 20
    def fn(d, s, im):
        panel(d, s, 0, 0, 920, hgt, r=34, border=col, ba=120)
        txt(d, s, 50, 52, sp.get("title", ""), F_TITLE, 58, P.white)
        txt(d, s, 52, 132, sp.get("kicker", ""), F_MONO, 28, col)
        for i, r in enumerate(rows):
            y = 200 + i * 128; sub = r.get("sub", "")
            d.rounded_rectangle((50 * s, y * s, 104 * s, (y + 54) * s), radius=12 * s, outline=hexrgb(P.white, 160), width=3 * s)
            txt(d, s, 130, y + (8 if sub else 27), r["text"], F_TITLE, 38, P.white, "la" if sub else "lm")
            if sub: txt(d, s, 132, y + 60, sub, F_MONO, 24, P.white, "la", 170)
    card = sprite(920, hgt, fn)
    tick = sprite(54, 54, lambda d, s, im: (d.rounded_rectangle((0, 0, 54 * s, 54 * s), radius=12 * s, fill=hexrgb(col)),
                                            d.line((14 * s, 28 * s, 24 * s, 39 * s, 41 * s, 17 * s), fill=hexrgb(P.night), width=6 * s, joint="curve")))
    def draw(frame, t, lt, dur):
        c = card.copy()
        for i, r in enumerate(rows):
            k = appear(t, lt(r.get("at", a + 0.9 + i * 1.4)), 0.25)
            if k > 0: c.alpha_composite(fade_img(tick, k), (50, 200 + i * 128))
        paste(frame, c, 540, 260 + hgt / 2 + 30 * (1 - appear(t, 0)), 1)
    ctx.run_layer("checklist", a, b, draw)


@scene
def end_card(ctx, sp):
    """Series cliffhanger: kicker, title, sub line, icon tiles, pulsing Follow pill and handle."""
    a, b = sp["start"], sp.get("end", 1e9)
    lines = sp.get("title", ["Part 2"])
    ph = 140 + 90 * len(lines) + (50 if sp.get("sub") else 0)
    def fn(d, s, im):
        panel(d, s, 0, 0, 920, ph, r=36, border=P.violet, ba=160)
        txt(d, s, 460, 60, sp.get("kicker", "NEXT"), F_MONO, 30, P.violet, "mm")
        for i, ln in enumerate(lines): txt(d, s, 460, 150 + i * 90, ln, F_TITLE, 74, P.white, "mm")
        if sp.get("sub"): txt(d, s, 460, 150 + len(lines) * 90 - 14, sp["sub"], F_MONO, 24, P.white, "mm", 170)
    card = sprite(920, ph, fn)
    tiles = [sprite(160, 160, lambda d, s, im, n=n: (panel(d, s, 0, 0, 160, 160, r=30, border=P.red, ba=140), icon(d, s, n, 40, 40, 80, P.red)))
             for n in sp.get("tiles", [])]
    follow = sprite(400, 100, lambda d, s, im: (panel(d, s, 0, 0, 400, 100, r=50, fill=P.green, a=255),
                                                txt(d, s, 200, 50, sp.get("follow", "+ Follow"), F_TITLE, 48, P.night, "mm")))
    handle = sprite(500, 44, lambda d, s, im: txt(d, s, 250, 22, sp.get("handle", ""), F_MONO, 28, P.white, "mm", 200))
    cy = 300 + ph / 2; ty = 300 + ph + 110; fy = ty + (170 if tiles else 0)
    def draw(frame, t, lt, dur):
        k = appear(t, 0, 0.4); paste(frame, card, 540, cy + 30 * (1 - k), k)
        for i, tl_ in enumerate(tiles):
            kt = (t - 0.3 - i * 0.15) / 0.4
            if kt > 0: paste(frame, tl_, 540 + (i - (len(tiles) - 1) / 2) * 190, ty, min(1, kt * 2), 0.7 + 0.3 * spring(kt))
        kf = (t - 0.8) / 0.4
        if kf > 0:
            pulse = 1 + 0.05 * math.sin(t * 5) if kf > 1 else 1
            paste(frame, follow, 540, fy, min(1, kf * 2), (0.6 + 0.4 * spring(kf)) * pulse)
            if sp.get("handle"): paste(frame, handle, 540, fy + 82, min(1, kf * 2))
    ctx.run_layer("end_card", a, min(b, ctx.raw_duration), draw, H=1300, edge=0.2, fade_out=False)


# ================================================================ demo helpers
@scene
def highlight(ctx, sp):
    """Pulsing outline around part of the screen (output-frame coords) with a label. For demos."""
    a, b = sp["start"], sp["end"]
    x, y, w, h = sp["rect"]
    col = colour(sp.get("color", "amber"))
    lab = pill(sp["label"], col, P.night, 28) if sp.get("label") else None
    def draw(frame, t, lt, dur):
        p = 0.5 + 0.5 * math.sin(t * 5)
        d = ImageDraw.Draw(frame)
        for k in range(3):
            grow = 4 + k * 6 * p
            d.rounded_rectangle((x - grow, y - grow, x + w + grow, y + h + grow), radius=18 + grow,
                                outline=hexrgb(col, int(255 * (1 - k * 0.35))), width=5 - k)
        if lab: paste(frame, lab, x + lab.width / 2, max(260, y - 40), appear(t, 0.1))
    ctx.run_layer("highlight", a, b, draw, H=1920)


@scene
def lower_third(ctx, sp):
    """Name/title strap above the captions."""
    a, b = sp["start"], sp["end"]
    w = max(tw(F_TITLE, 44, sp.get("title", "")), tw(F_MONO, 26, sp.get("sub", ""))) + 90
    im = sprite(w, 128, lambda d, s, im: (panel(d, s, 0, 0, w, 128, r=24, border=P.cyan, ba=150),
                                          d.rectangle((0, 24 * s, 8 * s, 104 * s), fill=hexrgb(P.cyan)),
                                          txt(d, s, 40, 46, sp.get("title", ""), F_TITLE, 44, P.white, "lm"),
                                          txt(d, s, 40, 94, sp.get("sub", ""), F_MONO, 26, P.cyan, "lm")))
    def draw(frame, t, lt, dur):
        k = appear(t, 0, 0.35); paste(frame, im, 60 + im.width / 2 - 40 * (1 - k), 1150, k)
    ctx.run_layer("lower_third", a, b, draw, H=1300)
