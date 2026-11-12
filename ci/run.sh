#!/usr/bin/env bash
# Entry point for the Reels workflow. Installs tools, then ci/bgjobs.py (jobs.py + background removal) works out what is pending and does it.
# Then ci/sfx.py adds the sound-effects variant (preview_sfx.mp4 / final_reel_sfx.mp4) for reels that have a sfx.json.
# Both run through ci/vrun.py, which adds variant reels (a second edit of the same upload, see ci/variants.py).
set -uo pipefail
set -a; source ci/config.env; set +a
mkdir -p _out
echo "::group::Install"
sudo apt-get update -qq >/dev/null && sudo apt-get install -y -qq ffmpeg espeak-ng >/dev/null
python -m pip install -q --upgrade pip >/dev/null
python -m pip install -q -r engine/requirements.txt
ffmpeg -hide_banner -version | head -1
echo "::endgroup::"
python ci/vrun.py bgjobs
status=$?
echo "bgjobs exit $status"
python ci/vrun.py sfx || echo "sfx failed (clean videos are unaffected)"
exit $status
