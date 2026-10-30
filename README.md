# Video-lab · Swati Talks Tech Reel pipeline (v2)

Raw talking-head or demo video → an edited 1080×1920 Instagram Reel whose graphics are designed for that
video. Claude plans and designs; GitHub Actions does the heavy work.

| Tool | Job |
|---|---|
| Whisper (faster-whisper) | transcript with a timing for every word |
| FFmpeg | iPhone HDR → SDR, cutting pauses and retakes, loudness, encoding |
| HyperFrames (HeyGen, open source) | the Reel's graphics, captions and motion as HTML + GSAP, checked and rendered to MP4 |
| yt-dlp | downloads reference Reels (with views/likes/comments) so what works can be studied |

## A Reel, start to finish (Swati's steps in bold)
1. **Create a release** on this repo: tag = short name (e.g. `ai-scams`), attach the raw video, Publish.
2. GitHub transcribes it and makes an edit-friendly copy (`reels/<slug>/`, `proxy.mp4` on the release).
3. **Tell Claude** "new reel: ai-scams". Claude researches what works, writes the storyboard, fact-checks, designs the composition.
4. GitHub checks it with HyperFrames and renders a draft: **watch `preview.mp4`** on the release, approve or ask for changes.
5. Claude approves the render; GitHub renders the final: **download `final_reel.mp4`**, post, then delete the release.

## Layout
- `engine/` topic-independent media work (`python3 -m engine prepare|timeline|build|preview|refs|finish`).
- `docs/REEL_GUIDE.md` how a Reel project is built. `docs/TECHNIQUES.md` the technique library + evidence scoreboard.
  `docs/techniques/` working scene for each technique. `docs/STYLE.md` living style notes.
- `reels/<slug>/` one Reel. `reels/glossary.txt` words Whisper should spell right.
- `references/queue.txt` reference Reels / topic searches to study; `references/<name>/` their analysis.
- `selftest/` an example Reel project; changing `selftest/run.txt` runs the whole pipeline (and the technique gallery).
- `ci/` everything the workflow runs. `.github/workflows/reels.yml` the one workflow file.
