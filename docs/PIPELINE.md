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
