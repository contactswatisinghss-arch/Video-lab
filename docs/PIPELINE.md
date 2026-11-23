# Pipeline v3 (12 Nov 2026): the default for every Reel

Swati: "use the updated pipeline for any new reel I post from here."

## What the final is
The final is **Swati's original upload, untouched**, with only the edit laid on top (`ci/overlay.py`):
same resolution (4K 2160x3840), same frame rate (60p), same HDR colours (HLG, bt2020), audio stream-copied
when nothing is cut. No grading, tone mapping, scaling, fps change or loudness change. Graphics are converted to the
raw's colour space only (SDR white -> HLG reference white). Verified on NvidiaScandal-yours: Swati saw no
change to her original quality.

- Composition scenes marked `data-layer="under"` on their host `<div>` are drawn BEHIND her (needs `bg_remove`, uses
  the person matte); everything else (cards, titles, captions) is drawn on top.
- Camera moves on `#cam` (punch-ins, slides, zooms) can't be reproduced on the raw yet -> that reel falls back to the
  old 1080p30 re-render. **Don't design `#cam` moves** unless Swati accepts that, and say so in the storyboard.
- Options in edit.json: `"final": {"mode": "rerender"}` (old path, only if she asks), `"graphics_res": "portrait-4k"`,
  `"graphics_fps": 60`, `"crf"`, `"preset"`.
- Previews are still a 1080p tone-mapped draft (an approximation for checking the edit); tell her so. The final is
  the original.

## Reuse
- One person cutout per upload + cut list (`cutout-<key>.webm` on the release), shared by preview, final and every
  variant (`"release": "<slug>"` in a variant's edit.json). Two versions never redo the transcript or the cutout.

## Measured timings (NvidiaScandal-yours, 12 Nov 2026, 78 s Reel)
| Step | Time |
|---|---|
| Upload -> transcript (prepare) | ~20 min |
| Background cutout (once per video) | ~45 min incl. setup |
| Graphics layers (over + under) | 13 min |
| Lay onto 4K60 original (compose, 2 cores) | 39 min |
| Final, cutout fresh | 1 h 52 min |
| Final, cutout reused | ~55 min |
Expectation to give Swati: **~2 h from raw upload to final, plus her review time.** Targets after the planned speed-ups
(both layers rendered in parallel, compose split by time across machines): ~1 h 20 min total.
Claude reports times after every Reel from status.json / release times (no tracking code in GitHub; Swati's call).

## Capacity
- GitHub Free: 20 parallel jobs; one Reel uses up to ~5 at once -> 3-4 Reels in parallel. Claude's storyboards are
  sequential (~20-30 min each).
- Monthly minutes are the limit: ~150 runner-min per Reel (one fix round), ~200 for two versions. Plan: 30 Reels/month
  on ONE account with an Actions spending budget (~$15-20/month). Never multiple free accounts (GitHub ToS).

## Workflow file
`ci/reels.yml` is the parallel workflow (plan / fast / matte / slow / sfx). It only takes effect once Swati pastes it
over `.github/workflows/reels.yml` (the connector can't write workflow files). Until then runs are sequential via
`ci/run.sh` -> `ci/vrun.py bgjobs`, which already uses the overlay final and the shared cutout.

## Still to do
- Render over/under layers in parallel; split compose into time segments (matrix) + concat.
- Sharper matte for 4K (faint light edge around hair on dark backgrounds, cutout is made at 1080p and scaled up).
- Camera moves in overlay mode.

## Stock b-roll, automatic (ci/broll.py, 23 Nov 2026)
Swati: "Workflow or Claude should be able to use the tool to do it" (no manual stock downloads).
- Claude writes `reels/<slug>/broll.txt`, one shot per line: `name | search words` (add `| photo` for photos only).
- On the next run GitHub fetches the top 3 candidates per shot: **Pixabay videos** (free Pixabay licence, no attribution)
  when the `PIXABAY_KEY` secret reaches the job, else **Wikimedia Commons photos** (free licences; credit them in the
  pinned comment from `broll/index.json`). Files become 1080x1920 (video: H.264, no audio, max 8 s) on the release as
  `broll-<name>-<k>.mp4|.jpg`; `reels/<slug>/broll/sheet.jpg` + `index.json` are committed for Claude to pick from.
- Compositions use `assets/broll-<name>-<k>.mp4|.jpg`; preview and final builds download only the referenced files.
- A failed or empty b-roll run retries on the next run; editing broll.txt re-runs it.
- Pexels is not used: its API key issuance is paused (Nov 2026) and its website blocks automated downloads.

### One-time setup for Pixabay video (Swati, ~3 min)
1. Pixabay account → https://pixabay.com/api/docs/ shows "Your API key" (green box) once logged in.
2. https://github.com/contactswatisinghss-arch/Video-lab/settings/secrets/actions → New repository secret →
   name `PIXABAY_KEY`, value = the key.
3. Edit `.github/workflows/reels.yml` on github.com (Claude can't push workflow files): under `YTDLP_COOKIES: ...` add
   `          PIXABAY_KEY: ${{ secrets.PIXABAY_KEY }}` (same indentation). `ci/reels.yml` already has it.
Without these steps b-roll still works, as Wikimedia photos.
