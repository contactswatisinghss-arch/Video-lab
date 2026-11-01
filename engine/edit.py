"""Edit decisions -> final timeline, base video and a buildable HyperFrames project.

reels/<slug>/
  transcript.json   words with ids w0..wN on the RAW clock (from prepare)
  edit.json         cuts, caption fixes, fonts, registry adds, cover, post text
  hf/               the Reel's HyperFrames project, designed for this video (index.html, compositions/, assets/)

Tokens Claude can write anywhere in hf/*.html|css|js (resolved at build time):
  {{at:w12}}  {{end:w12}}     final-timeline start / end of word w12 (seconds)   {{at:w12+0.3}} {{at:w12-0.2}}
  {{find:october}}            start of the first word whose text is "october"
  {{raw:12.5}}                raw second 12.5 mapped to the final timeline
  {{= find('government') - at(w12) + 0.5 }}   arithmetic on the above (at, end, find, raw, dur, min, max, round)
  {{dur}}                     final duration
  {{words}}                   JSON array of final words [{id,text,start,end}] (fixes applied)
  {{fontfaces}}               @font-face rules for edit.json "fonts"
  {{lib:captions}}            the caption helper library (engine/lib/captions.js)

edit.json "speed" (e.g. 1.1) plays the cut video faster with the pitch kept (FFmpeg atempo); every token,
{{dur}} and {{words}} is on the sped-up clock, so graphics stay on their words.
"""
import ast, json, math, os, re, shutil
from .util import run, ReelError

HERE = os.path.dirname(os.path.abspath(__file__))

def norm(w): return re.sub(r"[^\w%]", "", w).lower()

def load_transcript(path):
    j = json.load(open(path, encoding="utf-8"))
    words = [dict(id=w.get("id", f"w{i}"), w=w["w"].strip(), s=float(w["s"]), e=float(w["e"]))
             for i, w in enumerate(j.get("words", [])) if w.get("w", "").strip()]
    return words, float(j.get("duration") or (words[-1]["e"] + 1 if words else 0))

def apply_fixes(words, fixes):
    """[["php 2 shell", "PHP2Shell"]]: multi-word matches merge into one word (keeps the first id)."""
    alias = {}
    for src, dst in fixes or []:
        pat = [norm(x) for x in src.split() if norm(x)]
        if not pat: continue
        i, out = 0, []
        while i < len(words):
            if [norm(w["w"]) for w in words[i:i + len(pat)]] == pat:
                last = words[i + len(pat) - 1]
                tail = re.sub(r"^[\w%'’]+", "", last["w"])
                out.append(dict(id=words[i]["id"], w=dst + ("" if dst.endswith(tail) else tail), s=words[i]["s"], e=last["e"]))
                for w in words[i + 1:i + len(pat)]: alias[w["id"]] = words[i]["id"]
                i += len(pat)
            else:
                out.append(words[i]); i += 1
        words = out
    return words, alias

def plan_keeps(words, duration, cuts):
    pad, maxgap = cuts.get("pad", 0.10), cuts.get("max_pause", 0.40)
    removes = sorted([float(a), float(b)] for a, b in cuts.get("remove", []))
    removed = lambda t: any(a <= t < b for a, b in removes)
    keeps = []
    for w in words:
        if removed((w["s"] + w["e"]) / 2): continue
        a, b = max(0.0, w["s"] - pad), min(duration, w["e"] + pad)
        if keeps and a - keeps[-1][1] <= maxgap - 2 * pad: keeps[-1][1] = max(keeps[-1][1], b)
        else: keeps.append([a, b])
    if not keeps: return [[0.0, duration]]
    head = cuts.get("keep_head", 0.6)
    if head is True or (head and keeps[0][0] <= float(head)): keeps[0][0] = 0.0
    tail = cuts.get("keep_tail", 1.0)
    if tail is True: keeps[-1][1] = duration
    elif tail: keeps[-1][1] = min(duration, keeps[-1][1] + float(tail))
    for ra, rb in removes:
        nk = []
        for a, b in keeps:
            if rb <= a or ra >= b: nk.append([a, b]); continue
            if a < ra: nk.append([a, ra])
            if rb < b: nk.append([rb, b])
        keeps = [k for k in nk if k[1] - k[0] > 0.05]
    # snap to whole frames so the cut video and the token times agree exactly
    fps = float(cuts.get("fps", 30))
    snapped = []
    for a, b in keeps:
        a, b = math.floor(a * fps + 1e-6) / fps, min(duration, math.ceil(b * fps - 1e-6) / fps)
        if snapped and a <= snapped[-1][1]: snapped[-1][1] = max(snapped[-1][1], b)
        elif b - a > 0.05: snapped.append([a, b])
    return [[round(a, 4), round(b, 4)] for a, b in snapped]

def make_remap(keeps):
    def remap(t):
        off = 0.0
        for a, b in keeps:
            if t < a: return off
            if t <= b: return off + (t - a)
            off += b - a
        return off
    return remap

class Timeline:
    def __init__(self, transcript_path, edit):
        words, self.raw_duration = load_transcript(transcript_path)
        self.raw_words = {w["id"]: w for w in words}
        self.edit = edit
        fixed, self.alias = apply_fixes(words, edit.get("fixes"))
        self.keeps = plan_keeps(fixed, self.raw_duration, edit.get("cuts", {}))
        self.speed = float(edit.get("speed") or 1.0)
        if not 0.5 <= self.speed <= 2.0: raise ReelError(f"edit.json speed {self.speed} is outside 0.5-2.0")
        base, sp = make_remap(self.keeps), self.speed
        self.remap = lambda t: base(t) / sp
        self.duration = round(self.remap(self.raw_duration), 3)
        inside = lambda w: any(a <= (w["s"] + w["e"]) / 2 <= b for a, b in self.keeps)
        self.words = [dict(id=w["id"], text=w["w"], start=round(self.remap(w["s"]), 3),
                           end=round(self.remap(w["e"]), 3)) for w in fixed if inside(w)]

    def word(self, wid):
        wid = self.alias.get(wid, wid)
        w = self.raw_words.get(wid)
        if not w: raise ReelError(f"Token refers to unknown word id {wid}")
        return w

    def at(self, wid): return round(self.remap(self.word(wid)["s"]), 3)
    def end(self, wid): return round(self.remap(self.word(wid)["e"]), 3)

    def find(self, text, nth=1):
        """Start of the nth word matching `text` (final words with fixes first, then raw words)."""
        n, k = norm(text), 0
        for w in self.words:
            if norm(w["text"]) == n:
                k += 1
                if k == nth: return w["start"]
        k = 0
        for w in self.raw_words.values():
            if norm(w["w"]) == n:
                k += 1
                if k == nth: return round(self.remap(w["s"]), 3)
        raise ReelError(f"find('{text}'): no word '{text}' in the transcript")

    def to_json(self):
        return {"duration": self.duration, "raw_duration": self.raw_duration, "keeps": self.keeps, "speed": self.speed,
                "removed_seconds": round(self.raw_duration - self.duration, 2), "words": self.words}

EXPR = re.compile(r"\{\{=\s*(.+?)\s*\}\}")
_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Call, ast.Name, ast.Load, ast.Add, ast.Sub,
            ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Pow, ast.Mod, ast.FloorDiv)

def eval_expr(expr, tl, where=""):
    """{{= find('government') - at(w12) + 0.5 }}  ->  number. Functions: at, end, find, raw, max, min, round; name: dur.
    Word ids may be written bare (at(w12)) or quoted (at('w12'))."""
    expr2 = re.sub(r"\b(at|end)\(\s*(w\d+)\s*\)", r"\1('\2')", expr)
    tree = ast.parse(expr2, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED): raise ReelError(f"{where}: unsupported expression {{{{= {expr} }}}}")
        if isinstance(node, ast.Name) and node.id not in ("dur", "at", "end", "find", "raw", "max", "min", "round"):
            raise ReelError(f"{where}: unknown name '{node.id}' in {{{{= {expr} }}}}")
    env = {"__builtins__": {}, "dur": tl.duration, "at": tl.at, "end": tl.end, "find": tl.find,
           "raw": tl.remap, "max": max, "min": min, "round": round}
    return float(eval(compile(tree, "<expr>", "eval"), env))

TOKEN = re.compile(r"\{\{\s*(at|end|find|raw|dur|words|fontfaces|lib)(?::([^}+\-\s]+(?:\.\d+)?))?\s*([+-]\s*[\d.]+)?\s*\}\}")

def resolve(text, tl, fontfaces="", where=""):
    text = EXPR.sub(lambda m: f"{max(0.0, eval_expr(m.group(1), tl, where)):.3f}", text)
    def sub(m):
        kind, arg, off = m.group(1), m.group(2), m.group(3)
        off = float(off.replace(" ", "")) if off else 0.0
        if kind == "at": v = tl.at(arg)
        elif kind == "end": v = tl.end(arg)
        elif kind == "find": v = tl.find(arg)
        elif kind == "raw": v = tl.remap(float(arg))
        elif kind == "dur": v = tl.duration
        elif kind == "words": return json.dumps(tl.words, ensure_ascii=False)
        elif kind == "fontfaces": return fontfaces
        elif kind == "lib":
            p = os.path.join(HERE, "lib", f"{arg}.js")
            if not os.path.exists(p): raise ReelError(f"{where}: unknown library {{{{lib:{arg}}}}}")
            return open(p, encoding="utf-8").read()
        return f"{max(0.0, v + off):.3f}"
    return TOKEN.sub(sub, text)

def load_edit(reel_dir):
    p = os.path.join(reel_dir, "edit.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

GSAP_TAG = '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'

def harden_html(txt, fontfaces, is_root):
    """Safety net for HyperFrames rules that are easy to forget (they fail the render, not the local preview):
    the root page must load GSAP itself; each <template> scene is linted alone, so it needs its own @font-face."""
    if is_root and "gsap.timeline" in txt and not re.search(r'<script[^>]+src="[^"]*gsap(\.min)?\.js"', txt):
        txt = txt.replace("</head>", "  " + GSAP_TAG + "\n</head>", 1) if "</head>" in txt else GSAP_TAG + "\n" + txt
    if not is_root and fontfaces and txt.lstrip().startswith("<template") and "@font-face" not in txt:
        if "<style>" in txt: txt = txt.replace("<style>", "<style>\n" + fontfaces + "\n", 1)
        else: txt = txt.replace("<template>", "<template>\n<style>\n" + fontfaces + "\n</style>", 1)
    return txt

def build_project(reel_dir, out_dir, fontfaces=""):
    """Copy reels/<slug>/hf to out_dir with tokens resolved; write timeline.json. No video needed."""
    edit = load_edit(reel_dir)
    tl = Timeline(os.path.join(reel_dir, "transcript.json"), edit)
    src = os.path.join(reel_dir, "hf")
    if not os.path.exists(os.path.join(src, "index.html")): raise ReelError(f"{src}/index.html is missing")
    if os.path.exists(out_dir):
        keep = os.path.join(out_dir, "assets", "base.mp4")   # keep a built base video between builds
        for root, dirs, files in os.walk(out_dir, topdown=False):
            for f in files:
                p = os.path.join(root, f)
                if p != keep and "/.hyperframes" not in p and "/fonts/" not in p: os.remove(p)
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        os.makedirs(os.path.join(out_dir, rel), exist_ok=True)
        for f in files:
            sp, dp = os.path.join(root, f), os.path.join(out_dir, rel, f)
            if f.endswith((".html", ".css", ".js", ".json", ".svg", ".md")):
                txt = resolve(open(sp, encoding="utf-8").read(), tl, fontfaces, where=os.path.join(rel, f))
                if f.endswith(".html"): txt = harden_html(txt, fontfaces, is_root=(rel == "." and f == "index.html"))
                open(dp, "w", encoding="utf-8").write(txt)
            else:
                shutil.copy(sp, dp)
    json.dump(tl.to_json(), open(os.path.join(reel_dir, "timeline.json"), "w"), indent=1)
    json.dump(tl.to_json(), open(os.path.join(out_dir, "timeline.json"), "w"), indent=1)
    # the root's data-duration should match the cut length
    idx = open(os.path.join(out_dir, "index.html"), encoding="utf-8").read()
    m = re.search(r'data-composition-id="[^"]+"[^>]*data-duration="([\d.]+)"', idx) or \
        re.search(r'id="root"[^>]*data-duration="([\d.]+)"', idx)
    warn = []
    if m and abs(float(m.group(1)) - tl.duration) > 0.05:
        warn.append(f"index.html root data-duration={m.group(1)} but the cut is {tl.duration}s; use {{{{dur}}}}")
    return tl, warn

def build_base(proxy, tl, out, loudnorm=True, fps=30):
    """Cut the proxy to the kept segments in one pass, apply edit.json speed (pitch kept), normalise loudness,
    keyframe every second."""
    segs = tl.keeps
    parts, labels = [], []
    for i, (a, b) in enumerate(segs):
        parts.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}];"
                     f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.015,afade=t=out:st={max(0, b - a - 0.02):.3f}:d=0.02[a{i}]")
        labels.append(f"[v{i}][a{i}]")
    sp = float(getattr(tl, "speed", 1.0) or 1.0)
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(segs)}:v=1:a=1[vc][a0]"
    fc += f";[vc]setpts=PTS/{sp:.4f}[v]" if abs(sp - 1) > 1e-3 else ";[vc]null[v]"
    tempo = f"atempo={sp:.4f}," if abs(sp - 1) > 1e-3 else ""
    fc += ";[a0]" + tempo + ("loudnorm=I=-14:TP=-1.5:LRA=11," if loudnorm else "") + "aresample=48000[a]"
    script = out + ".filter.txt"; open(script, "w").write(fc)
    run(["ffmpeg", "-y", "-i", proxy, "-filter_complex_script", script, "-map", "[v]", "-map", "[a]",
         "-r", str(fps), "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-g", str(fps),
         "-keyint_min", str(fps), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", out])
    os.remove(script)
