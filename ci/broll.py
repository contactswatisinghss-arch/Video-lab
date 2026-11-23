"""Automatic b-roll for a Reel: no manual downloads for Swati.

reels/<slug>/broll.txt, one shot per line ("#" starts a comment):
    name | search words            e.g.   sf | san francisco skyline
    name | search words | photo    photos only (skip video)
On GitHub, for every changed broll.txt:
  1. Pixabay videos (free Pixabay licence, no attribution needed) when the repo secret PIXABAY_KEY reaches the job as
     the PIXABAY_KEY environment variable (one line in .github/workflows/reels.yml, see docs/PIPELINE.md);
  2. otherwise / no match: Wikimedia Commons photos (free licences; author + licence kept for the pinned comment).
The top 3 candidates per shot become 1080x1920 files (videos: H.264, no audio, max 8 s; photos: JPG), uploaded to the
reel's release as broll-<name>-<k>.mp4|.jpg, with reels/<slug>/broll/index.json (source, author, licence) and
reels/<slug>/broll/sheet.jpg (labelled contact sheet) committed so Claude can pick.
Compositions reference them as assets/broll-<name>-<k>.mp4|.jpg; the build downloads exactly the referenced ones.
"""
import glob, json, os, re, subprocess, sys, time, traceback, urllib.parse, urllib.request

UA = {"User-Agent": "VideoLab-reel-pipeline/1.0 (personal Instagram Reel editing)"}
W, H, MAX_S, PER_SHOT = 1080, 1920, 8, 3

def _get(url, timeout=60):
    for k in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or k == 3: raise
            time.sleep(10 * (k + 1))

def parse(path):
    shots = []
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if not line or "|" not in line: continue
        parts = [p.strip() for p in line.split("|")]
        name = re.sub(r"[^a-z0-9]+", "-", parts[0].lower()).strip("-")
        if name and parts[1]: shots.append({"name": name, "query": parts[1], "photo": len(parts) > 2 and parts[2].lower() == "photo"})
    return shots

def pixabay(query, key):
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": key, "q": query, "per_page": 12, "safe_search": "true", "order": "popular"})
    hits = json.loads(_get(url)).get("hits", [])
    out = []
    for h in hits:
        if h.get("duration", 0) < 4: continue
        v = h.get("videos", {})
        best = next((v[s] for s in ("large", "medium", "small") if v.get(s, {}).get("url") and v[s].get("width", 0) >= 960), None)
        if best: out.append({"kind": "video", "url": best["url"], "page": h.get("pageURL"), "author": h.get("user"), "license": "Pixabay Content License", "tags": h.get("tags")})
    return out

def wikimedia(query):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": query + " filetype:bitmap", "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 3840, "format": "json"})
    pages = (json.loads(_get(url)).get("query") or {}).get("pages", {})
    out = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        if not ii.get("thumburl") or ii.get("width", 0) < 1600 or not re.search(r"CC|Public domain|PD", lic, re.I): continue
        author = re.sub(r"<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()[:80]
        out.append({"kind": "photo", "url": ii["thumburl"], "page": ii.get("descriptionurl"), "author": author, "license": lic, "title": p.get("title")})
    return out

def convert(J, src, dst, kind):
    if kind == "video":
        J.sh(["ffmpeg", "-y", "-v", "error", "-i", src, "-t", str(MAX_S), "-an", "-vf",
              f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,format=yuv420p",
              "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-movflags", "+faststart", dst], timeout=600)
    else:
        J.sh(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "-q:v", "3", dst], timeout=300)

def sheet(items, path):
    from PIL import Image, ImageDraw
    tw, th, cols = 270, 480, 6
    rows = max(1, (len(items) + cols - 1) // cols)
    im = Image.new("RGB", (cols * (tw + 6) + 6, rows * (th + 6) + 6), (12, 14, 20))
    for i, (label, thumb) in enumerate(items):
        try: t = Image.open(thumb).convert("RGB").resize((tw, th))
        except Exception: t = Image.new("RGB", (tw, th), (60, 60, 60))
        d = ImageDraw.Draw(t); d.rectangle((0, th - 30, tw, th), fill=(0, 0, 0)); d.text((8, th - 24), label, fill=(255, 255, 255))
        im.paste(t, (6 + (i % cols) * (tw + 6), 6 + (i // cols) * (th + 6)))
    im.save(path, quality=85)

def release_of(slug):
    try: return (json.load(open(os.path.join("reels", slug, "edit.json"), encoding="utf-8")) or {}).get("release") or slug
    except Exception: return slug

def pending(J):
    out = []
    for p in sorted(glob.glob("reels/*/broll.txt")):
        slug = os.path.basename(os.path.dirname(p))
        st = (J.jload(J.status_path(slug), {}) or {}).get("broll") or {}
        if J.fhash(p) != st.get("hash") or not st.get("ok"): out.append(slug)   # failed runs retry next time
    return out

def job_broll(J, slug):
    d = os.path.join("reels", slug); src = os.path.join(d, "broll.txt"); h = J.fhash(src)
    work = os.path.join("_work", slug, "broll"); os.makedirs(work, exist_ok=True)
    od = os.path.join(d, "broll"); os.makedirs(od, exist_ok=True)
    key = os.environ.get("PIXABAY_KEY", "").strip()
    index, thumbs, files, notes = [], [], [], []
    try:
        for s in parse(src):
            cands = []
            if key and not s["photo"]:
                try: cands = pixabay(s["query"], key)
                except Exception as e: notes.append(f"{s['name']}: pixabay failed: {e}")
            if not cands:
                try: cands = wikimedia(s["query"]); time.sleep(2)
                except Exception as e: notes.append(f"{s['name']}: wikimedia failed: {e}")
            k = 0
            for c in cands[:PER_SHOT + 3]:
                if k >= PER_SHOT: break
                ext = "mp4" if c["kind"] == "video" else "jpg"
                raw = os.path.join(work, f"{s['name']}-{k + 1}.src")
                name = f"broll-{s['name']}-{k + 1}.{ext}"; out = os.path.join(work, name)
                try:
                    open(raw, "wb").write(_get(c["url"], timeout=180))
                    convert(J, raw, out, c["kind"])
                    th = out[:-4] + "-thumb.jpg"
                    if ext == "mp4": J.sh(["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", out, "-frames:v", "1", "-vf", "scale=270:480", th], check=False)
                    else:
                        from PIL import Image
                        Image.open(out).convert("RGB").resize((270, 480)).save(th, quality=85)
                    k += 1
                    files.append(out); thumbs.append((name[6:], th))
                    index.append({"shot": s["name"], "query": s["query"], "file": name, **{x: c.get(x) for x in ("kind", "page", "author", "license", "title", "tags")}})
                except Exception as e:
                    notes.append(f"{name}: {e}")
            if k == 0: notes.append(f"{s['name']}: no usable result for '{s['query']}'")
        if files: J.upload(release_of(slug), *files)
        sheet(thumbs, os.path.join(od, "sheet.jpg"))
        J.jsave(os.path.join(od, "index.json"), {"source": "pixabay+wikimedia" if key else "wikimedia (no PIXABAY_KEY)", "items": index, "notes": notes})
        J.changed_paths.update([os.path.join(od, "sheet.jpg"), os.path.join(od, "index.json")])
        J.set_status(slug, "broll", bool(files), {"hash": h, "count": len(files), "pixabay": bool(key), "notes": notes[-10:]})
    except Exception as e:
        J.set_status(slug, "broll", False, {"hash": h}, err=f"{e}\n{traceback.format_exc()}")
    J.changed_paths.add(J.status_path(slug))

def fetch_used(J, slug, out_dir):
    """Download the broll-* files a built composition references into its assets/ folder."""
    used = set()
    for p in glob.glob(os.path.join(out_dir, "**", "*.html"), recursive=True):
        used.update(re.findall(r"assets/(broll-[\w.-]+\.(?:mp4|jpg))", open(p, encoding="utf-8", errors="ignore").read()))
    for name in sorted(used):
        if not os.path.exists(os.path.join(out_dir, "assets", name)):
            J.download_asset(release_of(slug), name, os.path.join(out_dir, "assets"))
    return used

def apply(J, B):
    _build = J.build
    def build(slug, reel_dir=None, proxy=None):
        out, edit = _build(slug, reel_dir=reel_dir, proxy=proxy)
        try: fetch_used(J, slug, out)
        except Exception: J.log(traceback.format_exc()); raise
        return out, edit
    J.build = build

    _main = B.main
    def main():
        todo = pending(J)
        if todo:
            os.makedirs("_out", exist_ok=True)
            J.LOG = open("_out/log.txt", "a", encoding="utf-8")
            for slug in todo:
                J.log(f"\n======== broll {slug} ========")
                try: job_broll(J, slug)
                except Exception: J.log(traceback.format_exc())
                try: J.commit(f"reel-bot: broll {slug}"); J.changed_paths.clear()
                except Exception: J.log(traceback.format_exc())
        _main()
    B.main = main
