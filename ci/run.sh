#!/usr/bin/env bash
# Entry point for the Reels workflow. Installs tools, then ci/bgjobs.py (jobs.py + background removal) works out what is pending and does it.
# Then ci/sfx.py adds the sound-effects variant (preview_sfx.mp4 / final_reel_sfx.mp4) for reels that have a sfx.json.
set -uo pipefail
set -a; source ci/config.env; set +a
mkdir -p _out
echo "::group::Install"
sudo apt-get update -qq >/dev/null && sudo apt-get install -y -qq ffmpeg espeak-ng >/dev/null
python -m pip install -q --upgrade pip >/dev/null
python -m pip install -q -r engine/requirements.txt
ffmpeg -hide_banner -version | head -1
echo "::endgroup::"
python ci/bgjobs.py
status=$?
echo "bgjobs.py exit $status"
python ci/sfx.py || echo "sfx.py failed (clean videos are unaffected)"
exit $status
