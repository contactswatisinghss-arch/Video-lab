#!/usr/bin/env bash
# Tool install shared by every job of ci/reels.yml.
set -uo pipefail
set -a; source ci/config.env; set +a
mkdir -p _out
sudo apt-get update -qq >/dev/null && sudo apt-get install -y -qq ffmpeg espeak-ng >/dev/null
python -m pip install -q --upgrade pip >/dev/null
python -m pip install -q -r engine/requirements.txt
ffmpeg -hide_banner -version | head -1
