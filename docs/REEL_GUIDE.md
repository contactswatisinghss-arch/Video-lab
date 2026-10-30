# Reel project guide (pipeline v2: FFmpeg + Whisper + HyperFrames + yt-dlp)

Each Reel is designed from scratch for its topic. Nothing visual is a fixed template: the engine only does
what never changes (transcribe, cut pauses, colour, loudness, render plumbing). The look, the graphics and the
motion are a HyperFrames composition Claude writes for that video, starting from the technique library
(`docs/TECHNIQUES.md`) and the HyperFrames registry, adapted every time.

## Folder of one Reel: `reels/<slug>/`

| File | Who writes it | What |
|---|---|---|
| `transcript.json`, `transcript.txt`, `words.tsv` | prepare (GitHub) | Whisper words with ids `w0..wN` on the RAW clock |
| `meta.json`, `frames.jpg` | prepare | format, audio levels, warnings; a contact sheet of the raw footage |
| `BRIEF.md` | Claude | audience, angle, hook, research evidence, storyboard (beats × techniques), facts + sources |
| `edit.json` | Claude | cuts, word fixes, fonts, registry blocks to add, cover time, post caption |
| `hf/` | Claude | the HyperFrames project: `index.html`, `compositions/*.html`, `assets/*.svg` |
| `timeline.json` | build | final timeline (kept segments, words on the final clock) |
| `preview/` | preview (GitHub) | `check.json`, `review-beats.jpg`, `review-phone.jpg`, `sheet.jpg` (real footage) |
| `RENDER` | Claude, after Swati approves | any text, e.g. `approved 2026-10-30`; changing it re-renders the final |
| `PREPARE` | Claude (rare) | change it to re-run transcription (e.g. after adding glossary words) |
| `status.json` | GitHub | per stage: ok, time, errors/log tail, links. Read this; Actions logs are not visible to Claude |
| `review/` | final | `sheet.jpg`, `cover.jpg` of the delivered Reel |

The release `<slug>` holds the big files: the raw video (Swati), `proxy.mp4`, `preview.mp4`, `final_reel.mp4`,
`cover.jpg`, `caption.txt`.

## edit.json

```json
{
  "version": 2,
  "cuts": {"max_pause": 0.4, "pad": 0.1, "keep_head": 0.6, "keep_tail": 1.2, "remove": [[12.3, 15.8]]},
  "fixes": [["php 2 shell", "PHP2Shell"], ["SPA", "SBI"]],
  "fonts": ["Space Grotesk", "Archivo Black"],
  "hf_add": ["grain-overlay"],
  "cover_at": 1.0,
  "audio": {"loudnorm": true},
  "post": {"caption": "...", "hashtags": ["#..."]}
}
```

- `cuts.remove`: raw-second ranges to drop (retakes, false starts, tangents, a slow intro). Pauses over `max_pause` are cut automatically.
- `fixes`: Whisper mishearings → correct text (multi-word phrases merge into one caption word).
- `fonts`: any Google Fonts family; fetched into `assets/fonts` and exposed via `{{fontfaces}}`. HyperFrames bundles Inter, JetBrains Mono, Montserrat, Oswald, Archivo Black, Space Mono, IBM Plex Mono, EB Garamond, Playfair Display, Poppins and a few more.
- `hf_add`: HyperFrames registry items installed on GitHub with `hyperframes add` (use for items with binary assets; plain-text items can simply be copied into `hf/compositions/`).
- `cover_at`: second on the FINAL timeline for `cover.jpg`.

## Time tokens (write the composition against spoken words, not seconds)

Resolved at build time in any `hf/` text file, so graphics stay on their word when cuts change.

| Token | Value |
|---|---|
| `{{at:w57}}` / `{{end:w57}}` | final-timeline start / end of word `w57` (`{{at:w57+0.2}}`, `{{at:w57-0.3}}`) |
| `{{find:denmark}}` | start of the first word "denmark" (fixed text first) |
| `{{raw:42.5}}` | raw second 42.5 on the final timeline |
| `{{dur}}` | final length |
| `{{= find('japan') - at(w40) + 0.5 }}` | arithmetic: `at`, `end`, `find`, `raw`, `dur`, `min`, `max`, `round` |
| `{{words}}` | JSON array of final words `[{id,text,start,end}]` for captions |
| `{{fontfaces}}` | `@font-face` rules for `edit.json` fonts (put it in a `<style>`) |
| `{{lib:captions}}` | inlines `engine/lib/captions.js` (caption grouping, fit, timing, clean exits) |

Inside a scene, GSAP positions are scene-local: write `const S = <scene start token>;` once and use
`{{at:w63}} - S` for word-synced beats (see `selftest/hf/compositions/places.html`).

## HyperFrames essentials (full rules: the hyperframes skill, `skills/hyperframes/` in github.com/heygen-com/hyperframes)

- `index.html` root: `data-composition-id`, `data-start="0"`, `data-duration="{{dur}}"`, `data-width="1080"`, `data-height="1920"`, `data-fps="30"`.
- Footage: a timed wrapper `div.clip` (start 0, duration `{{dur}}`) → an untimed `#cam` div (punch-ins and reframes are GSAP transforms on it) → `<video src="assets/base.mp4" data-has-audio="true" playsinline>` (no timing on the video itself).
- One scene per beat: a host `<div id="x" data-composition-id="x" data-composition-src="compositions/x.html" data-start=… data-duration=… data-track-kind="graphics">`. The scene file puts style, markup and script inside `<template>`, styles its root as `#root`, builds ONE paused timeline and registers `window.__timelines["x"] = tl`. Host id = scene id = timeline key.
- Captions: one host with `data-track-kind="captions"` for the whole film.
- `fromTo`, never `from`; no `Math.random`, `Date.now`, timers, network, `repeat: -1`; never tween `display`/`visibility` on a `.clip`; no CSS `transform` on an element GSAP transforms; unique, prefixed ids across all scenes (`#pl-head`, not `#title`); select by those ids in scripts.
- Fonts other than the bundled ones need `{{fontfaces}}`. Asset paths are `assets/...`, no leading slash. Icons and diagrams as inline SVG.
- Motion craft: arrivals on long-tailed ease-outs (`expo.out`, `power4.out`), exits 40–50 % shorter, words stagger 60–120 ms, a landed title holds still, 3–5 transition kinds caused by something on screen, no floating/pulsing loops, no slow creeping scale. Read `motion.md` in the HyperFrames skill before designing.
- Before hand-building a named effect (map, chart, kinetic type, lower third, glitch, grain), look in `docs/TECHNIQUES.md` and the registry: `registry/blocks/*` and `registry/components/*` in the HyperFrames repo (about 450 items, plain HTML you can copy and restyle).

## Vertical layout (1080×1920, Instagram)

- Nothing in the top 168 px; every word between 168 and 1330 px; below 1330 only texture. No text under the right-hand action rail (~x > 980 in the lower half).
- Captions centred around y 1190–1260 (above Instagram's caption/buttons). The face usually sits around y 650–1250: graphics live in the top band (200–900) or replace the frame briefly (a full-screen beat), never parked on the face for long.
- Frame 0 is the thumbnail: the hook title is already on screen in the first frame.
- Text sizes: titles 110–190 px, body 40–60 px, labels ≥ 26 px; check legibility on `review-phone.jpg`.

## The loop

1. Locally: `python3 -m engine timeline --reel reels/<slug>` and `python3 -m engine preview --reel reels/<slug> --times 0.2,3,8,… --out sheet.jpg` (stand-in footage, a mini runtime; catches script errors, layout and timing).
2. Push `edit.json` + `hf/` → GitHub runs HyperFrames `check`, review sheets and a draft render; read `status.json` (`preview.check.top_errors`) and look at `preview/review-beats.jpg`, `preview/review-phone.jpg`, `preview/sheet.jpg`. Fix every error; weigh warnings.
3. Swati watches `preview.mp4` on the release. On approval write `RENDER`.
4. GitHub renders at delivery quality → `final_reel.mp4` on the release.

## References and research (yt-dlp)

`references/queue.txt` takes two kinds of line:
- `name url`: one Reel/Short (Instagram, YouTube, TikTok). GitHub downloads it with yt-dlp and writes
  `references/<name>/analysis.json` (views, likes, comments, followers, like rate; cuts, average shot length, words per
  second, hook words, loudness), `hook.jpg` (first 3 s), `frames.jpg`, `transcript.txt`. The video is never committed.
- `search name query words`: searches YouTube Shorts for the topic, writes `references/<name>/search.json` (results
  ranked by views with likes/comments) and analyses the top 3 in `top1/ top2/ top3/`. Instagram has no public search, so
  Instagram examples come from web search + their URLs.

If a site blocks the download, Swati can attach the video to a release tagged `ref-<name>`. Claude then looks at
`hook.jpg`/`frames.jpg`, writes `references/<name>/notes.md` (techniques spotted, hook mechanics, pacing, caption style,
graphic density, palette roles) and updates the scoreboard in `docs/TECHNIQUES.md`. References give grammar, never content to copy.
