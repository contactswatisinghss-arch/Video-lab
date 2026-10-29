"""Reel engine: talking-head / demo video -> 1080x1920 Instagram Reel.

  python3 -m engine.reel prepare  --video raw.mp4 --out reels/<slug>          # transcript + checks
  python3 -m engine.reel render   --video raw.mp4 --plan reels/<slug>/plan.json --out out/
  python3 -m engine.reel sheet    --plan reels/<slug>/plan.json --out sheet.jpg  # storyboard preview, no video needed
  python3 -m engine.reel selftest --out selftest/                              # synthetic end-to-end run

Every time in plan.json is a second on the RAW video (as in transcript.json). The engine cuts
pauses, so it maps raw seconds to the final timeline itself.
"""
import argparse, glob, hashlib, json, os, re, shutil, subprocess, sys, time
from PIL import Image, ImageDraw, ImageFilter
from .common import *
from . import common
from .scenes import SCENES

VERSION = "1.0.0"
FPS = 30


# ================================================================== transcript
def load_words(path):
    if not path or not os.path.exists(path): return []
    j = json.load(open(path, encoding="utf-8"))
    return [dict(w=w["w"].strip(), s=float(w["s"]), e=float(w["e"])) for w in j.get("words", []) if w.get("w", "").strip()]

def _norm(w): return re.sub(r"[^\w%]", "", w).lower()

def apply_fixes(words, fixes):
    """fixes: [["php 2 shell", "PHP2Shell"], ["SPA", "SBI"]] - multi-word matches merge into one word."""
    for src, dst in fixes or []:
        pat = [_norm(x) for x in src.split() if _norm(x)]
        if not pat: continue
        i, out = 0, []
        while i < len(words):
            seg = [_norm(w["w"]) for w in words[i:i + len(pat)]]
            if seg == pat:
                tail = re.sub(r"^[\w%']+", "", words[i + len(pat) - 1]["w"])  # keep trailing punctuation
                out.append(dict(w=dst + (tail if not dst.endswith(tail) else ""), s=words[i]["s"], e=words[i + len(pat) - 1]["e"]))
                i += len(pat)
            else:
                out.append(words[i]); i += 1
        words = out
    return words


# ================================================================== cuts
def plan_keeps(words, duration, cuts):
    pad, maxgap = cuts.get("pad", 0.10), cuts.get("max_pause", 0.40)
    removes = sorted(cuts.get("remove", []))
    def removed(t): return any(a <= t < b for a, b in removes)
    keeps = []
    for w in words:
        if removed((w["s"] + w["e"]) / 2): continue
        a, b = max(0.0, w["s"] - pad), min(duration, w["e"] + pad)
        if keeps and a - keeps[-1][1] <= maxgap - 2 * pad: keeps[-1][1] = max(keeps[-1][1], b)
        else: keeps.append([a, b])
    if not keeps: return [[0.0, duration]]
    if keeps[0][0] < cuts.get("keep_head", 0.8): keeps[0][0] = 0.0
    tail = cuts.get("keep_tail", True)
    if tail is True: keeps[-1][1] = duration
    elif tail: keeps[-1][1] = min(duration, keeps[-1][1] + float(tail))
    # carve explicit removals out of the keeps
    for ra, rb in removes:
        nk = []
        for a, b in keeps:
            if rb <= a or ra >= b: nk.append([a, b]); continue
            if a < ra: nk.append([a, ra])
            if rb < b: nk.append([rb, b])
        keeps = [k for k in nk if k[1] - k[0] > 0.05]
    return keeps

def make_remap(keeps):
    def remap(t):
        off = 0.0
        for a, b in keeps:
            if t < a: return off
            if t <= b: return off + (t - a)
            off += b - a
        return off
    return remap

def plan_shots(keeps, zooms, punches):
    shots = []
    for i, (a, b) in enumerate(keeps):
        pts = sorted({a, b} | {z[k] for z in zooms for k in ("start", "end") if a < z[k] < b})
        for x, y in zip(pts, pts[1:]):
            if y - x < 0.04: continue
            mid = (x + y) / 2
            z = next((z for z in zooms if z["start"] <= mid < z["end"]), None)
            if z: shots.append((x, y, ("rect", z["rect"])))
            else:
                s = 1.15 if any(a <= p <= b for p in punches) else (1.0 if i % 2 == 0 else 1.08)
                shots.append((x, y, ("scale", s)))
    return shots


# ================================================================== context: layers + ASS events
class Ctx:
    def __init__(self, work, remap, raw_duration, final_len, sample_times=None):
        self.work, self.remap, self.raw_duration, self.final_len = work, remap, raw_duration, final_len
        self.layers, self.events, self.sample_times, self.samples, self._n = [], [], sample_times, {}, 0

    def run_layer(self, name, raw_a, raw_b, draw, H=1100, edge=0.25, fade_in=True, fade_out=True):
        START, END = self.remap(raw_a), self.remap(min(raw_b, self.raw_duration))
        dur = max(END - START, 1 / FPS)
        def lt(raw): return self.remap(raw) - START
        def frame_at(t):
            frame = Image.new("RGBA", (1080, H), (0, 0, 0, 0)); draw(frame, t, lt, dur)
            a = (ease(t / edge) if fade_in else 1) * ((1 - ease((t - (dur - edge)) / edge)) if fade_out else 1)
            if a < 0.999: frame.putalpha(frame.getchannel("A").point(lambda v: int(v * a)))
            return frame
        self._n += 1
        if self.sample_times is not None:
            for ts in self.sample_times:
                if START <= ts <= START + dur: self.samples.setdefault(ts, []).append(frame_at(ts - START))
            return
        folder = os.path.join(self.work, f"g{self._n:02d}_{name}")
        shutil.rmtree(folder, ignore_errors=True); os.makedirs(folder)
        prev, prev_path = None, None
        for f in range(int(dur * FPS) + 1):
            frame = frame_at(f / FPS)
            path = os.path.join(folder, f"{f:05d}.png"); key = hashlib.md5(frame.tobytes()).digest()
            if key == prev:
                try: os.link(prev_path, path)
                except OSError: shutil.copy(prev_path, path)
            else:
                frame.save(path, compress_level=1); prev, prev_path = key, path
        self.layers.append((folder, START))

    @staticmethod
    def t_ass(t):
        t = max(0.0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
        return f"{h}:{m:02d}:{s:05.2f}"
    def ev_out(self, style, A, B, text, layer=1):
        if B - A > 0.05: self.events.append(f"Dialogue: {layer},{self.t_ass(A)},{self.t_ass(B)},{style},,0,0,0,,{text}")
    def ev(self, style, a, b, text, layer=1):
        self.ev_out(style, self.remap(a), self.remap(b), text, layer)


def rrect(w, h, r):
    w, h, r = round(w), round(h), round(min(r, w / 2, h / 2)); k = round(r * 0.448)
    return (f"m {r} 0 l {w-r} 0 b {w-k} 0 {w} {k} {w} {r} l {w} {h-r} b {w} {h-k} {w-k} {h} {w-r} {h} "
            f"l {r} {h} b {k} {h} 0 {h-k} 0 {h-r} l 0 {r} b 0 {k} {k} 0 {r} 0")

def shape(ctx, x, y, w, h, r, tags, layer=1, A=0.0, B=None, raw=False):
    f = ctx.ev if raw else ctx.ev_out
    f("Shape", A, ctx.final_len if B is None else B, f"{{\\an5\\pos({x:.0f},{y:.0f}){tags}\\p1}}{rrect(w, h, r)}{{\\p0}}", layer)


# ================================================================== captions + branding
CAP_FS, CAP_Y, CAP_MAXW, ROW_GAP = 86, 1340, 920, 96
POP = "\\alpha&HFF&\\fscx55\\fscy55\\t(0,60,\\alpha&H00&)\\t(0,110,\\fscx110\\fscy110)\\t(110,190,\\fscx100\\fscy100)"
BOX_POP = "\\fscx70\\fscy70\\t(0,110,\\fscx106\\fscy106)\\t(110,190,\\fscx100\\fscy100)"

def caption_lines(words, keeps, cap):
    inside = lambda w: any(a <= (w["s"] + w["e"]) / 2 <= b for a, b in keeps)
    hide = cap.get("hide", [])
    words = [w for w in words if inside(w) and not any(a <= w["s"] < b for a, b in hide)]
    mx, mc = cap.get("max_words", 4), cap.get("max_chars", 24)
    lines, cur = [], []
    for w in words:
        if cur and (len(cur) >= mx or w["s"] - cur[-1]["e"] > 0.45 or re.search(r"[.?!:;]$", cur[-1]["w"])
                    or len(" ".join(x["w"] for x in cur + [w])) > mc):
            lines.append(cur); cur = []
        cur.append(w)
    if cur: lines.append(cur)
    out = []
    for i, ln in enumerate(lines):
        nxt = lines[i + 1][0]["s"] if i + 1 < len(lines) else ln[-1]["e"] + 0.8
        out.append((ln, min(nxt, ln[-1]["e"] + 0.6)))
    return out

def build_captions(ctx, words, keeps, cap):
    keys = sorted([(k, P.red) for k in cap.get("red", [])] + [(k, P.green) for k in cap.get("green", [])],
                  key=lambda kc: -len(kc[0]))
    def key_span(ws):
        nw = [_norm(w) for w in ws]
        for phrase, col in keys:
            p = [_norm(x) for x in phrase.split()]
            for i in range(len(nw) - len(p) + 1):
                if p and nw[i:i + len(p)] == p: return i, i + len(p) - 1, col
        return None
    style_case = cap.get("case", "as_spoken")
    for ln, end in caption_lines(words, keeps, cap):
        ws = [re.sub(r"[{}\\]", "", w["w"]) for w in ln]
        if style_case == "upper": ws = [w.upper() for w in ws]
        if not any(ws): continue
        fs = CAP_FS
        space = ass_text_w(F_CAP, fs, " ") + 12
        ww = [ass_text_w(F_CAP, fs, w) for w in ws]
        ks = key_span(ws)
        gl, gr = [0.0] * len(ws), [0.0] * len(ws)
        if ks: gl[ks[0]], gr[ks[1]] = 14, 14
        gap = [l + r for l, r in zip(gl, gr)]
        ww = [w + g for w, g in zip(ww, gap)]
        def roww(ix): return sum(ww[i] for i in ix) + space * (len(ix) - 1)
        rows = [list(range(len(ws)))]
        if roww(rows[0]) * 0.82 > CAP_MAXW and len(ws) > 1:
            cut = min(range(1, len(ws)), key=lambda c: max(roww(range(c)), roww(range(c, len(ws)))))
            rows = [list(range(cut)), list(range(cut, len(ws)))]
        widest = max(roww(r) for r in rows)
        if widest > CAP_MAXW:
            s = CAP_MAXW / widest
            fs, space, ww = fs * s, space * s, [w * s for w in ww]
            gl, gr, gap = [g * s for g in gl], [g * s for g in gr], [g * s for g in gap]
        pos = {}
        for ri, r in enumerate(rows):
            y = CAP_Y + (ri - (len(rows) - 1) / 2) * ROW_GAP
            x = 540 - roww(r) / 2
            for i in r:
                l = x + gl[i]; pos[i] = (l, l + ww[i] - gap[i], y); x += ww[i] + space
        starts = [w["s"] for w in ln]
        if ks and pos[ks[0]][2] != pos[ks[1]][2]: ks = None
        if ks:
            i0, i1, col = ks
            x0, x1, y = pos[i0][0] - 20, pos[i1][1] + 20, pos[i0][2]
            ctx.ev("Shape", starts[i0], end, f"{{\\an5\\pos({(x0 + x1) / 2:.0f},{y + fs * 0.03:.0f})\\1c{ass_col(col)}"
                   f"\\bord0\\shad0\\blur0.6{BOX_POP}\\p1}}{rrect(x1 - x0, fs * 1.12, 14)}{{\\p0}}", layer=5)
        for i, w in enumerate(ws):
            x0, x1, y = pos[i]
            look = (("\\c" + ass_col(P.night) if ks[2] == P.green else "") + "\\bord0\\shad0") if ks and ks[0] <= i <= ks[1] else "\\blur5"
            size = "" if fs == CAP_FS else f"\\fs{fs:.1f}"
            ctx.ev("Cap", starts[i], end, f"{{\\an5\\pos({(x0 + x1) / 2:.0f},{y:.0f}){size}{look}{POP}}}{w}", layer=6)

def build_branding(ctx, brand):
    if not brand: return
    TAG_Y, TAG_H, TAG_FS = 196, 70, 38
    t1, t2 = brand.get("tag", ""), ("  ·  " + brand["tag2"]) if brand.get("tag2") else ""
    w1, w2 = ass_text_w(F_MONO, TAG_FS, t1), ass_text_w(F_MONO, TAG_FS, t2)
    tag_w, x0 = 28 + 18 + 16 + w1 + w2 + 30, 48
    shape(ctx, x0 + tag_w / 2, TAG_Y, tag_w, TAG_H, TAG_H / 2,
          f"\\1c{ass_col(P.night)}\\1a&H40&\\3c{ass_col(P.cyan)}\\3a&HA0&\\bord2\\shad0", layer=20)
    dot_x = x0 + 37
    shape(ctx, dot_x, TAG_Y, 18, 18, 9, f"\\1c{ass_col(P.cyan)}\\bord0\\shad0\\blur0.6", layer=22)
    for k in range(int(ctx.final_len // 2) + 1):
        shape(ctx, dot_x, TAG_Y, 18, 18, 9, f"\\1a&HFF&\\3c{ass_col(P.cyan)}\\3a&H30&\\bord2\\shad0\\fscx100\\fscy100"
              f"\\t(0,900,\\fscx260\\fscy260\\3a&HFF&)", layer=21, A=k * 2.0, B=min(k * 2.0 + 0.9, ctx.final_len))
    ctx.ev_out("Tag", 0, ctx.final_len, f"{{\\an4\\pos({dot_x + 25:.0f},{TAG_Y})}}{t1}{{\\c{ass_col(P.cyan)}}}{t2}", layer=23)
    if brand.get("part"):
        pw = ass_text_w(F_MONO, TAG_FS, brand["part"]) + 56
        shape(ctx, 1032 - pw / 2, TAG_Y, pw, TAG_H, TAG_H / 2, f"\\1c{ass_col(P.violet)}\\bord0\\shad0\\blur0.6", layer=20)
        ctx.ev_out("Tag", 0, ctx.final_len, f"{{\\an5\\pos({1032 - pw / 2:.0f},{TAG_Y})}}{brand['part']}", layer=23)

def text_card(ctx, sp):
    style = sp.get("style", "Card")
    txt_ = sp["text"].replace("\n", "\\N")
    for name in ("red", "green", "cyan", "violet"):
        txt_ = txt_.replace("{" + name + "}", "{\\c" + ass_col(getattr(P, name)) + "}")
    txt_ = txt_.replace("{/}", "{\\c" + ass_col(P.white) + "}")
    ctx.ev(style, sp["start"], sp["end"], "{\\fad(140,140)}" + f"{{\\an8\\pos(540,{sp.get('y', 330)})}}" + txt_)

def write_ass(ctx, path):
    WHITE, BOX = ass_col(P.white), ass_col(P.night, 0x26)
    open(path, "w", encoding="utf-8").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{N_CAP},{CAP_FS},{WHITE},{WHITE},{ass_col(P.night, 0x70)},{ass_col(P.night, 0x60)},0,0,0,0,100,100,0,0,1,6,3,5,0,0,0,1
Style: Shape,{N_CAP},20,{WHITE},{WHITE},{WHITE},&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Tag,{N_MONO},38,{WHITE},{WHITE},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Card,{N_TITLE},64,{WHITE},{WHITE},{BOX},{BOX},0,0,0,0,100,100,0,0,3,26,0,8,80,80,0,1
Style: Title,{N_TITLE},110,{WHITE},{WHITE},{BOX},{BOX},0,0,0,0,100,100,2,0,3,30,0,8,60,60,0,1
Style: Mono,{N_MONO},60,{WHITE},{WHITE},{BOX},{BOX},0,0,0,0,100,100,0,0,3,26,0,8,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ctx.events) + "\n")


# ================================================================== video steps
def make_proxy(video, meta, out, fps):
    tonemap = ""
    if meta["transfer"] in ("arib-std-b67", "smpte2084"):
        if "zscale" in run(["ffmpeg", "-hide_banner", "-filters"]):
            tonemap = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
                       "zscale=t=bt709:m=bt709:r=tv,")
    vertical = meta["width"] / meta["height"] < 0.65
    if vertical:
        fc = f"[0:v]{tonemap}scale=1440:2560:force_original_aspect_ratio=increase,crop=1440:2560,fps={fps},format=yuv420p[v]"
    else:   # landscape / square: sharp copy in the middle over a blurred, darkened fill
        fc = (f"[0:v]{tonemap}fps={fps},split[a][b];"
              "[a]scale=1440:2560:force_original_aspect_ratio=increase,crop=1440:2560,boxblur=30:3,eq=brightness=-0.18[bg];"
              "[b]scale=1440:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
    cmd = ["ffmpeg", "-y", "-i", video, "-filter_complex", fc, "-map", "[v]"]
    cmd += (["-map", "0:a:0", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"] if meta["has_audio"]
            else ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-map", "1:a", "-shortest", "-c:a", "aac"])
    run(cmd + ["-c:v", "libx264", "-crf", "16", "-preset", "veryfast", out])

def cut_shots(proxy, shots, work, fps, fast=False):
    listfile = os.path.join(work, "list.txt")
    with open(listfile, "w") as L:
        for i, (a, b, (kind, val)) in enumerate(shots):
            dur = b - a
            if kind == "scale":
                z = val
                vf = (f"crop=w=trunc(iw/{z}/2)*2:h=trunc(ih/{z}/2)*2:x=(iw-ow)/2:y=(ih-oh)*0.35,"
                      "scale=1080:1920:flags=lanczos,setsar=1")
            else:
                PW, PH = 1440, 2560; x, y, w, h = val
                cw = max(w * PW, h * PH * 9 / 16, 240); ch = cw * 16 / 9
                if ch > PH: ch = PH; cw = ch * 9 / 16
                cx, cy = (x + w / 2) * PW, (y + h / 2) * PH
                x0 = min(max(0, cx - cw / 2), PW - cw); y0 = min(max(0, cy - ch / 2), PH - ch)
                vf = f"crop={int(cw)//2*2}:{int(ch)//2*2}:{int(x0)}:{int(y0)},scale=1080:1920:flags=lanczos,setsar=1"
            af = f"afade=t=in:d=0.02,afade=t=out:st={max(0, dur - 0.03):.3f}:d=0.03"
            seg = os.path.join(work, f"seg{i:03d}.mp4")
            run(["ffmpeg", "-y", "-ss", f"{a:.3f}", "-i", proxy, "-t", f"{dur:.3f}", "-vf", vf, "-af", af, "-r", str(fps),
                 "-c:v", "libx264", "-crf", "14" if not fast else "24", "-preset", "veryfast" if not fast else "ultrafast",
                 "-c:a", "aac", "-b:a", "192k", "-ar", "48000", seg])
            L.write(f"file '{os.path.abspath(seg)}'\n")
    return listfile


# ================================================================== render
def load_plan(path):
    plan = json.load(open(path, encoding="utf-8"))
    apply_style(plan.get("style", "briefing"), plan.get("palette"))
    return plan

def setup(plan, words, raw_duration):
    words = apply_fixes(words, plan.get("captions", {}).get("fixes"))
    keeps = plan_keeps(words, raw_duration, plan.get("cuts", {}))
    remap = make_remap(keeps)
    return words, keeps, remap, remap(raw_duration)

def build_overlays(ctx, plan, words, keeps):
    build_captions(ctx, words, keeps, plan.get("captions", {}))
    build_branding(ctx, plan.get("brand"))
    for sp in plan.get("scenes", []):
        typ = sp.get("type")
        if typ == "text_card": text_card(ctx, sp); continue
        if typ not in SCENES: raise ReelError(f"Unknown scene type '{typ}'. Known: text_card, " + ", ".join(SCENES))
        print(f"   scene {typ} {sp.get('start')}-{sp.get('end')}", flush=True)
        SCENES[typ](ctx, sp)

def render(video, plan_path, transcript, out, work, fast=False):
    t_start = time.time()
    ensure_fonts(); plan = load_plan(plan_path)
    global FPS
    fps = FPS = int(plan.get("fps", 30))
    os.makedirs(out, exist_ok=True); os.makedirs(work, exist_ok=True)
    meta = probe(video)
    words, keeps, remap, final_len = setup(plan, load_words(transcript), meta["duration"])
    print(f"1/5 {len(words)} words, {len(keeps)} shots kept, {meta['duration']:.0f}s -> {final_len:.0f}s", flush=True)
    proxy = os.path.join(work, "proxy.mp4")
    sig = os.path.join(work, "proxy.sig"); want = f"{os.path.getsize(video)}-{fps}-v2"
    if not (os.path.exists(proxy) and os.path.exists(sig) and open(sig).read() == want):
        print("2/5 Making the edit-friendly copy (slowest step)...", flush=True)
        make_proxy(video, meta, proxy, fps); open(sig, "w").write(want)
    else: print("2/5 Edit-friendly copy cached.", flush=True)
    print("3/5 Cutting pauses, zooms and punch-ins...", flush=True)
    shots = plan_shots(keeps, plan.get("zooms", []), plan.get("punch_ins", []))
    seg_dir = os.path.join(work, "segs"); shutil.rmtree(seg_dir, ignore_errors=True); os.makedirs(seg_dir)
    listfile = cut_shots(proxy, shots, seg_dir, fps, fast)
    print("4/5 Drawing captions and graphics...", flush=True)
    gdir = os.path.join(work, "graphics"); shutil.rmtree(gdir, ignore_errors=True); os.makedirs(gdir)
    ctx = Ctx(gdir, remap, meta["duration"], final_len)
    build_overlays(ctx, plan, words, keeps)
    ass = os.path.join(work, "overlays.ass"); write_ass(ctx, ass)
    print(f"5/5 Rendering ({len(ctx.layers)} graphic layers)...", flush=True)
    inputs, chain, last = ["-f", "concat", "-safe", "0", "-i", listfile], [], "0:v"
    for k, (folder, start) in enumerate(ctx.layers):
        inputs += ["-framerate", str(fps), "-i", os.path.join(folder, "%05d.png")]
        chain.append(f"[{k+1}:v]setpts=PTS+{start:.3f}/TB[g{k}];[{last}][g{k}]overlay=0:0:eof_action=pass[v{k}]")
        last = f"v{k}"
    chain.append(f"[{last}]ass={ass.replace(':', chr(92) + ':')}:fontsdir={FONTS.replace(':', chr(92) + ':')},format=yuv420p[vout]")
    af = "aresample=async=1" + (",loudnorm=I=-14:TP=-1.5:LRA=11" if plan.get("audio", {}).get("loudnorm", True) else "")
    final = os.path.join(out, "final_reel.mp4")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "0:a", "-af", af,
         "-ar", "48000", "-r", str(fps), "-c:v", "libx264", "-crf", "18" if not fast else "26",
         "-preset", "medium" if not fast else "veryfast", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", final])
    run(["ffmpeg", "-y", "-ss", f"{plan.get('cover_at', 1.2):.2f}", "-i", final, "-frames:v", "1", "-q:v", "2",
         os.path.join(out, "cover.jpg")])
    n = 12
    run(["ffmpeg", "-y", "-i", final, "-vf", f"fps={n}/{max(final_len, 1):.2f},scale=240:-2,tile=6x2:padding=6",
         "-frames:v", "1", "-q:v", "4", os.path.join(out, "sheet.jpg")])
    post = plan.get("post", {})
    if post:
        open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(
            post.get("caption", "").strip() + "\n\n" + " ".join(post.get("hashtags", [])) + "\n")
    info = {"engine": VERSION, "final_seconds": round(final_len, 2), "raw_seconds": round(meta["duration"], 2),
            "shots": len(shots), "layers": len(ctx.layers), "render_seconds": round(time.time() - t_start)}
    json.dump(info, open(os.path.join(out, "render_info.json"), "w"), indent=2)
    print(f"Done: {final} ({final_len:.0f}s) in {info['render_seconds']}s", flush=True)
    return info


# ================================================================== storyboard sheet (no video needed)
def sheet(plan_path, transcript, out, duration=None, times=None):
    ensure_fonts(); plan = load_plan(plan_path)
    words = load_words(transcript)
    if duration is None:
        mp = os.path.join(os.path.dirname(transcript or plan_path), "meta.json")
        duration = json.load(open(mp))["duration"] if os.path.exists(mp) else ((words[-1]["e"] + 3) if words else 60)
    words, keeps, remap, final_len = setup(plan, words, duration)
    scenes = plan.get("scenes", [])
    if times is None:
        frac = lambda s: 0.4 if s["type"].startswith("hook") else 0.7      # hooks: catch the title on screen
        times = [remap(min(s["start"] + frac(s) * (min(s.get("end", duration), duration) - s["start"]), duration))
                 for s in scenes if s.get("type") != "text_card"]
    ctx = Ctx(None, remap, duration, final_len, sample_times=times)
    build_overlays(ctx, plan, words, keeps)
    lines = caption_lines(words, keeps, plan.get("captions", {}))
    tiles = []
    for ts in times:
        bg = Image.new("RGBA", (1080, 1920), hexrgb("#3a3f4a"))
        g = Image.linear_gradient("L").resize((1080, 1920)); bg.alpha_composite(tint(g, "#6b5a4c", 0.6))
        ImageDraw.Draw(bg).ellipse((290, 620, 790, 1240), fill=hexrgb("#55505a"))      # stand-in for the face
        for fr in ctx.samples.get(ts, []): bg.alpha_composite(fr, (0, 0))
        cap = next((" ".join(w["w"] for w in ln) for ln, end in lines if remap(ln[0]["s"]) <= ts <= remap(end)), "")
        d = ImageDraw.Draw(bg)
        if cap: d.text((540, 1340), cap, font=font(F_CAP, 40), fill=hexrgb(P.white), anchor="mm",
                       stroke_width=6, stroke_fill=hexrgb(P.night))
        d.rounded_rectangle((20, 1800, 1060, 1900), radius=20, fill=hexrgb(P.night, 230))
        d.text((540, 1850), f"{int(ts // 60)}:{ts % 60:04.1f}", font=font(F_MONO, 24), fill=hexrgb(P.white), anchor="mm")
        tiles.append(bg.convert("RGB").resize((270, 480), Image.LANCZOS))
    cols = 4; rows = max(1, (len(tiles) + cols - 1) // cols)
    grid = Image.new("RGB", (cols * 276 + 6, rows * 486 + 6), (12, 14, 20))
    for i, t_ in enumerate(tiles): grid.paste(t_, (6 + (i % cols) * 276, 6 + (i // cols) * 486))
    grid.save(out, quality=88)
    print(f"Sheet: {out} ({len(tiles)} frames, final length {final_len:.0f}s)")


# ================================================================== prepare (transcribe + checks)
def prepare(video, out, glossary=None, model=None):
    os.makedirs(out, exist_ok=True)
    meta = probe(video)
    wav = os.path.join(out, "_audio.wav")
    run(["ffmpeg", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav])
    vd = subprocess.run(["ffmpeg", "-i", wav, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mean = float((re.search(r"mean_volume: (-?[\d.]+)", vd) or [0, -99])[1])
    peak = float((re.search(r"max_volume: (-?[\d.]+)", vd) or [0, -99])[1])
    from faster_whisper import WhisperModel
    name = model or os.environ.get("WHISPER_MODEL", "medium.en")
    prompt = open(glossary, encoding="utf-8").read().strip() if glossary and os.path.exists(glossary) else None
    wm = WhisperModel(name, device="cpu", compute_type="int8")
    segs, info = wm.transcribe(wav, word_timestamps=True, beam_size=5, initial_prompt=prompt, vad_filter=False)
    words, seg_lines = [], []
    for sgm in segs:
        ws = [dict(w=w.word.strip(), s=round(w.start, 3), e=round(w.end, 3), p=round(w.probability, 3)) for w in (sgm.words or [])]
        words += ws
        seg_lines.append(f"[{sgm.start:7.2f} - {sgm.end:7.2f}] " + " ".join(f"{w['w']}({w['s']:.2f})" for w in ws))
    os.remove(wav)
    json.dump({"model": name, "language": info.language, "duration": meta["duration"], "words": words},
              open(os.path.join(out, "transcript.json"), "w", encoding="utf-8"), indent=1)
    open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8").write("\n".join(seg_lines) + "\n")
    warn = []
    if meta["width"] / meta["height"] >= 0.65: warn.append("Landscape/square source: framed over a blurred fill. Use zooms for screen content.")
    if meta["transfer"] in ("arib-std-b67", "smpte2084"): warn.append("HDR source: will be converted to standard range.")
    if mean < -32: warn.append(f"Audio is quiet (mean {mean} dB); loudness normalisation will lift it but noise rises too.")
    if peak > -0.2: warn.append(f"Audio peaks at {peak} dB: possible clipping/distortion.")
    if meta["duration"] > 100: warn.append(f"Raw length {meta['duration']:.0f}s: consider tighter cuts or a 2-part split (sweet spot 35-90s).")
    low = [w for w in words if w.get("p", 1) < 0.5]
    if low: warn.append(f"{len(low)} low-confidence words (check names/jargon): " + ", ".join(f"{w['w']}@{w['s']:.1f}" for w in low[:25]))
    meta.update({"audio_mean_db": mean, "audio_peak_db": peak, "words": len(words), "warnings": warn, "engine": VERSION})
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=2)
    # contact sheet of the raw video (one frame every few seconds) for Claude to see the shots
    fdir = os.path.join(out, "_frames"); os.makedirs(fdir, exist_ok=True)
    step = max(2.0, meta["duration"] / 30)
    run(["ffmpeg", "-y", "-i", video, "-vf", f"fps=1/{step:.2f},scale=-2:320", "-q:v", "5", os.path.join(fdir, "%03d.jpg")])
    ensure_fonts()
    ims = sorted(glob.glob(os.path.join(fdir, "*.jpg")))
    if ims:
        th = [Image.open(p).convert("RGB") for p in ims]; tw_, th_ = th[0].size
        cols = 6; rows = (len(th) + cols - 1) // cols
        grid = Image.new("RGB", (cols * tw_, rows * th_), (0, 0, 0)); d = ImageDraw.Draw(grid)
        for i, im in enumerate(th):
            x, y = (i % cols) * tw_, (i // cols) * th_; grid.paste(im, (x, y))
            t = i * step
            d.rectangle((x, y, x + 90, y + 30), fill=(0, 0, 0)); d.text((x + 6, y + 4), f"{t:5.1f}s", fill=(255, 255, 255), font=font(F_MONO, 10))
        grid.save(os.path.join(out, "frames.jpg"), quality=70)
    shutil.rmtree(fdir, ignore_errors=True)
    print(json.dumps({"words": len(words), "warnings": warn}, indent=1))


# ================================================================== selftest
SELFTEST_SCRIPT = ("They are calling it Black October. Seventy percent of websites run on PHP. "
                   "Government sites went down in Japan and Denmark. The flaw leaked before the fix. "
                   "Now it is patched, so ask your host to update PHP. Part two is coming, so follow.")

def selftest(out):
    os.makedirs(out, exist_ok=True)
    wav, raw = os.path.join(out, "speech.wav"), os.path.join(out, "raw.mp4")
    run(["espeak-ng", "-v", "en-us", "-s", "150", "-w", wav, SELFTEST_SCRIPT])
    d = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav]).strip()) + 3
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"gradients=s=1080x1920:r=30:c0=0x2a3442:c1=0x6b5a4c:speed=0.01:d={d:.2f}",
         "-i", wav, "-af", "apad", "-t", f"{d:.2f}", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-c:a", "aac", raw])
    prepare(raw, out, model=os.environ.get("WHISPER_MODEL", "small.en"))
    words = load_words(os.path.join(out, "transcript.json"))
    def at(word, default):
        w = next((w for w in words if _norm(w["w"]) == word), None); return w["s"] if w else default
    D = d
    plan = {"style": "briefing", "brand": {"tag": "SWATI TALKS TECH", "tag2": "BRIEFING", "part": "PART 1/2"},
            "captions": {"red": ["Black October", "leaked", "70%", "down"], "green": ["patched"], "fixes": [["seventy percent", "70%"]]},
            "punch_ins": [0.5],
            "scenes": [
                {"type": "hook_globe", "start": 0, "end": at("seventy", 3.5), "title": [["BLACK", "white"], ["OCTOBER", "red"]],
                 "kicker": "SELF-TEST", "title_out": at("seventy", 3.5) - 0.4, "pings": [{"lat": 46.6, "lon": 2.3, "at": 0.8}]},
                {"type": "stat_meter", "start": at("seventy", 3.5), "end": at("government", 6.5),
                 "sticker": {"value": 70, "suffix": "%", "label": "OF WEBSITES RUN ON PHP"},
                 "meter": {"label": "CVSS SEVERITY", "value": 9.2, "max": 10, "tag": "CRITICAL"}},
                {"type": "globe_pins", "start": at("government", 6.5), "end": at("flaw", 10),
                 "pins": [{"name": "Denmark", "lat": 56, "lon": 10, "at": at("denmark", 8)}, {"name": "Japan", "lat": 36.2, "lon": 138.3, "at": at("japan", 7.5)}],
                 "callouts": [{"start": at("government", 6.5), "end": at("flaw", 10), "icon": "building", "kicker": "GOVERNMENT SITES DOWN", "text": "Japan · Denmark"}]},
                {"type": "timeline", "start": at("flaw", 10), "end": at("now", 12.5), "alert_at": at("leaked", 11), "alert_index": 1,
                 "items": [{"at": at("flaw", 10), "icon": "calendar", "date": "22 OCT", "text": "Fix planned", "color": "green"},
                           {"at": at("leaked", 11), "icon": "drop", "date": "21 OCT", "text": "Flaw leaked", "color": "red"}]},
                {"type": "shield_versions", "start": at("now", 12.5), "end": at("part", D - 4), "title": "PATCHED",
                 "subtitle": "FIXED VERSIONS", "chips": ["PHP 8.5.12", "PHP 8.4.27"]},
                {"type": "end_card", "start": at("part", D - 4), "end": D, "kicker": "NEXT · PART 2", "title": ["When hackers hit", "the real world"],
                 "tiles": ["building", "card", "fridge"], "handle": "@swatitalkstech"}],
            "post": {"caption": "Self-test", "hashtags": ["#test"]}}
    pp = os.path.join(out, "plan.json"); json.dump(plan, open(pp, "w"), indent=1)
    sheet(pp, os.path.join(out, "transcript.json"), os.path.join(out, "storyboard.jpg"), duration=d)
    info = render(raw, pp, os.path.join(out, "transcript.json"), os.path.join(out, "render"), os.path.join(out, "_work"), fast=True)
    text = " ".join(w["w"] for w in words)
    ok = len(words) > 20 and "october" in text.lower()
    res = {"ok": ok, "words": len(words), "transcript": text, **info, "time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
    json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=2)
    print(json.dumps(res, indent=1))
    if not ok: raise ReelError("Self-test transcript looks wrong")


# ================================================================== cli
def pick_input(folder):
    vids = [p for p in glob.glob(os.path.join(folder, "*")) if re.search(r"\.(mp4|mov|m4v|mkv|webm)$", p, re.I)
            and not os.path.basename(p).startswith(("final_reel", "preview"))]
    if not vids: raise ReelError(f"No video found in {folder}. Attach the raw video to the GitHub release.")
    print(max(vids, key=os.path.getsize))

def main(argv=None):
    ap = argparse.ArgumentParser(prog="reel")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--video", required=True); p.add_argument("--out", required=True)
    p.add_argument("--glossary"); p.add_argument("--model")
    r = sub.add_parser("render"); r.add_argument("--video", required=True); r.add_argument("--plan", required=True)
    r.add_argument("--transcript"); r.add_argument("--out", required=True); r.add_argument("--work", default="_work")
    r.add_argument("--fast", action="store_true")
    s = sub.add_parser("sheet"); s.add_argument("--plan", required=True); s.add_argument("--transcript")
    s.add_argument("--out", required=True); s.add_argument("--duration", type=float)
    s.add_argument("--times", help="comma-separated final-timeline seconds")
    t = sub.add_parser("selftest"); t.add_argument("--out", required=True)
    k = sub.add_parser("pick-input"); k.add_argument("folder")
    a = ap.parse_args(argv)
    if a.cmd == "prepare": prepare(a.video, a.out, a.glossary, a.model)
    elif a.cmd == "render":
        tr = a.transcript or os.path.join(os.path.dirname(a.plan), "transcript.json")
        render(a.video, a.plan, tr, a.out, a.work, a.fast)
    elif a.cmd == "sheet":
        tr = a.transcript or os.path.join(os.path.dirname(a.plan), "transcript.json")
        sheet(a.plan, tr, a.out, a.duration, [float(x) for x in a.times.split(",")] if a.times else None)
    elif a.cmd == "selftest": selftest(a.out)
    elif a.cmd == "pick-input": pick_input(a.folder)

if __name__ == "__main__":
    try: main()
    except ReelError as e:
        print("\nERROR:", e, file=sys.stderr); sys.exit(1)
