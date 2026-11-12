"""Variant reels: a second (or third) edit of the SAME uploaded video, rendered side by side.

reels/<variant>/edit.json with "release": "<slug>" (e.g. reels/NvidiaScandal-yours -> "release": "NvidiaScandal"):
  - uses <slug>'s release for the raw video, proxy and cutout cache (no second upload for Swati)
  - uploads its outputs to that same release with the variant name added:
      preview.mp4 -> preview--<variant>.mp4, preview_sfx.mp4 -> preview_sfx--<variant>.mp4,
      final_reel.mp4 -> final_reel--<variant>.mp4, cover.jpg -> cover--<variant>.jpg, caption.txt -> caption--<variant>.txt
  - gets reels/<slug>/transcript.json copied in at run time when it has none (not committed)
Applied by ci/bgjobs.py and ci/sfx.py; plain reels are untouched.

Also (opt-in with edit.json "hdr": "original"; default is the tone-mapped proxy, which Swati preferred): the build can use proxy-original.mp4, made once from the raw iPhone HDR
video WITHOUT tone mapping (keeps the camera look Swati sees on her phone; Swati, 12 Nov 2026: the tone-mapped
proxy made her skin warmer/pinker and the picture darker). Cached on the release; no re-transcription needed.
"""
import glob, json, os, shutil

RENAMED = ("preview.mp4", "preview_sfx.mp4", "final_reel.mp4", "final_reel_sfx.mp4", "cover.jpg", "caption.txt")

def release_of(tag):
    try: return (json.load(open(os.path.join("reels", tag, "edit.json"), encoding="utf-8")) or {}).get("release") or tag
    except Exception: return tag

def vname(tag, name):
    if release_of(tag) == tag or name not in RENAMED: return name
    b, e = os.path.splitext(name)
    return f"{b}--{tag}{e}"

def link_transcripts():
    for p in glob.glob("reels/*/edit.json"):
        d = os.path.dirname(p); tag = os.path.basename(d); rel = release_of(tag)
        src = os.path.join("reels", rel, "transcript.json")
        if rel != tag and not os.path.exists(os.path.join(d, "transcript.json")) and os.path.exists(src):
            shutil.copy(src, os.path.join(d, "transcript.json"))

def apply(J):
    ra, da, up = J.release_assets, J.download_asset, J.upload

    def release_assets(tag):
        return ra(release_of(tag))

    def download_asset(tag, name, dest_dir):
        rel = release_of(tag)
        if rel == tag: return da(tag, name, dest_dir)
        real = vname(tag, name)
        p = da(rel, real, dest_dir)
        if real != name:
            q = os.path.join(dest_dir, name); os.replace(p, q); p = q
        return p

    def upload(tag, *files):
        rel = release_of(tag)
        if rel == tag: return up(tag, *files)
        out = []
        for f in files:
            n = vname(tag, os.path.basename(f))
            if n != os.path.basename(f):
                g = os.path.join(os.path.dirname(f), n); shutil.copy(f, g); f = g
            out.append(f)
        return up(rel, *out)

    J.release_assets, J.download_asset, J.upload = release_assets, download_asset, upload

    gp = J.get_proxy
    def get_proxy(slug):
        # Swati, 12 Nov 2026 (7:30 AM, final word): the first colours (tone-mapped) are closest to her phone; "original" looked flat/yellow.
        # Default = tonemap; "hdr": "original" only if she asks.
        try: mode = (json.load(open(os.path.join("reels", slug, "edit.json"), encoding="utf-8")) or {}).get("hdr") or "tonemap"
        except Exception: mode = "tonemap"
        try: prepared = (json.load(open(os.path.join("reels", release_of(slug), "meta.json"), encoding="utf-8")) or {}).get("hdr_mode")
        except Exception: prepared = None
        if mode == "tonemap" or prepared == "original": return gp(slug)
        rel = release_of(slug); name = "proxy-original.mp4"
        work = os.path.join("_work", rel); os.makedirs(work, exist_ok=True)
        p = os.path.join(work, name)
        if os.path.exists(p): return p
        if any(n == name for n, _ in ra(rel)): return da(rel, name, work)
        from engine.media import probe, make_proxy
        raw = da(rel, J.raw_asset(rel), os.path.join("in", rel))
        make_proxy(raw, probe(raw), p, hdr_mode="original")
        up(rel, p)
        return p
    J.get_proxy = get_proxy
    link_transcripts()
