# Video-lab · Swati Talks Tech Reel pipeline

Raw talking-head or demo video → edited 1080×1920 Instagram Reel, with Claude planning the edit and
GitHub Actions doing the heavy rendering.

## How a Reel goes through (what Swati does is in bold)
1. **Create a release** on this repo: tag = the Reel's short name (e.g. `black-october`), attach the raw video, Publish.
2. `Prepare reel` workflow transcribes it (Whisper, word timings), checks audio/format, and commits
   `reels/<slug>/transcript.json`, `transcript.txt`, `meta.json`, `frames.jpg`, `status.json`.
3. **Tell Claude** "new reel: <slug>". Claude reads those files, researches and fact-checks, and drafts the storyboard with a preview sheet.
4. **Approve** (or ask for changes). Claude pushes `reels/<slug>/plan.json`.
5. `Render reel` workflow renders the full-quality Reel and attaches `final_reel.mp4`, `cover.jpg`, `caption.txt` to the release.
6. **Download** `final_reel.mp4` from the release page, post, then delete the release to free space.

## Layout
- `engine/` – the editing engine (`python3 -m engine.reel prepare|render|sheet|selftest`).
- `docs/PLAN_GUIDE.md` – plan.json format and the scene template catalogue.
- `docs/examples/` – Black October plan (reference for a full news explainer).
- `reels/<slug>/` – per-Reel transcript, plan, status, review images. `reels/glossary.txt` – words Whisper should spell right.
- `.github/workflows/` – prepare, render, self-test. `ci/` – small helpers.

Engine version: see `VERSION` in `engine/reel.py`. The Claude skill "talking-head-reel-editor" drives all of this.
