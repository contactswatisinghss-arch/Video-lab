"""Fetch Google Fonts families (from the google/fonts GitHub repo) into a project's assets/fonts and
emit @font-face rules. HyperFrames bundles a few families (Inter, JetBrains Mono, ...); everything
else needs a font file in assets/fonts."""
import json, os, re, shutil, subprocess, urllib.request
from .util import CACHE, ReelError

BUNDLED = {"inter", "montserrat", "outfit", "nunito", "oswald", "league gothic", "archivo black", "space mono",
           "ibm plex mono", "jetbrains mono", "eb garamond", "playfair display", "source code pro", "noto sans jp",
           "roboto", "open sans", "lato", "poppins"}

def _dirname(family): return re.sub(r"[^a-z0-9]", "", family.lower())

def _fetch_dir_api(lic, d):
    url = f"https://api.github.com/repos/google/fonts/contents/{lic}/{d}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "reel-engine"})
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok and not tok.startswith("proxy"): req.add_header("Authorization", f"Bearer {tok}")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def _download(url, dest):
    with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f: shutil.copyfileobj(r, f)

def _fetch_git(family, d, cache):
    """Fallback without the API: sparse checkout of just that family's folder."""
    tmp = os.path.join(CACHE, "gfonts-git")
    if not os.path.exists(os.path.join(tmp, ".git")):
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse",
                        "https://github.com/google/fonts.git", tmp], check=True)
    for lic in ("ofl", "apache", "ufl"):
        subprocess.run(["git", "-C", tmp, "sparse-checkout", "add", f"{lic}/{d}"], capture_output=True)
        p = os.path.join(tmp, lic, d)
        if os.path.isdir(p):
            got = []
            for f in os.listdir(p):
                if f.endswith(".ttf"): shutil.copy(os.path.join(p, f), os.path.join(cache, f)); got.append(f)
            if got: return got
    return []

def fetch_family(family):
    """Returns list of local ttf paths for the family (cached)."""
    d = _dirname(family)
    cache = os.path.join(CACHE, "gfonts", d); os.makedirs(cache, exist_ok=True)
    have = [f for f in os.listdir(cache) if f.endswith(".ttf")]
    if not have:
        for lic in ("ofl", "apache", "ufl"):
            try:
                items = _fetch_dir_api(lic, d)
            except Exception:
                continue
            for it in items:
                if it["name"].endswith(".ttf"):
                    _download(it["download_url"], os.path.join(cache, it["name"])); have.append(it["name"])
            if have: break
        if not have:
            try: have = _fetch_git(family, d, cache)
            except Exception: have = []
    if not have: raise ReelError(f"Font family '{family}' not found in google/fonts")
    return [os.path.join(cache, f) for f in sorted(have)]

def _weight_range(fname):
    if "[" in fname and "wght" in fname: return "100 900"
    m = re.search(r"-(Thin|ExtraLight|Light|Regular|Medium|SemiBold|Bold|ExtraBold|Black)", fname)
    table = {"Thin": 100, "ExtraLight": 200, "Light": 300, "Regular": 400, "Medium": 500, "SemiBold": 600,
             "Bold": 700, "ExtraBold": 800, "Black": 900}
    return str(table.get(m.group(1), 400)) if m else "400"

def install_fonts(families, assets_dir):
    """Copy fonts into assets/fonts, return @font-face CSS."""
    if not families: return ""
    out = os.path.join(assets_dir, "fonts"); os.makedirs(out, exist_ok=True)
    css = []
    for fam in families:
        fam = fam.split(":")[0].strip()
        if fam.lower() in BUNDLED: continue
        for p in fetch_family(fam):
            name = os.path.basename(p)
            italic = "Italic" in name
            safe = name.replace("[", "_").replace("]", "_").replace(",", "_")
            shutil.copy(p, os.path.join(out, safe))
            css.append(f"@font-face{{font-family:'{fam}';src:url('assets/fonts/{safe}') format('truetype');"
                       f"font-weight:{_weight_range(name)};font-style:{'italic' if italic else 'normal'};font-display:block;}}")
    return "\n".join(css)
