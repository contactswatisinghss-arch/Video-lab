import os, subprocess, io, zipfile, urllib.request

class ReelError(RuntimeError):
    pass

def run(cmd, quiet=True, cwd=None, env=None):
    r = subprocess.run(cmd, capture_output=quiet, text=True, cwd=cwd, env=env)
    if r.returncode != 0:
        tail = ((r.stderr or "") + (r.stdout or ""))[-3000:] if quiet else ""
        raise ReelError("Command failed: " + " ".join(map(str, cmd))[:500] + "\n" + tail)
    return r.stdout if quiet else ""

CACHE = os.environ.get("REEL_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "reel_engine"))

_UI_FONTS = {  # only for contact-sheet labels
    "mono": ("https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip",
             "fonts/ttf/JetBrainsMono-Bold.ttf"),
}

def font_path(kind="mono"):
    url, member = _UI_FONTS[kind]
    d = os.path.join(CACHE, "fonts"); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, os.path.basename(member))
    if not os.path.exists(p):
        z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url, timeout=120).read()))
        name = next(n for n in z.namelist() if n.endswith(member))
        open(p, "wb").write(z.read(name))
    return p
