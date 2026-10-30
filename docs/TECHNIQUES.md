# Editing technique library

A superset that keeps growing. Each technique has a working HyperFrames scene in `docs/techniques/hf/compositions/`
(previewed locally, rendered on GitHub as part of the self-test) to ADAPT per Reel: restyle, retime to words, rewrite
copy. Never drop one in unchanged; the same scene twice in a feed looks templated.

Claude picks techniques per video in the storyboard; Swati approves. Every pick should be justified by the video type,
the beat, and evidence from the reference research (scoreboard below).

| # | Technique | What it does | Best for | Scene | Build notes |
|---|---|---|---|---|---|
| 1 | Orbit | Related items circle a central subject; depth from scale/opacity | "everything connects to X" (one tool, many uses; one flaw, many victims) | `orbit.html` | one linear tween drives the angle; place items from it (deterministic). Real 3D: registry `orbit-card` (Three.js) |
| 2 | Cork wall (evidence board) | Notes pin on as named, red string links them | timelines of an incident, "how they're connected", investigations | `corkwall.html` | notes drop with back-ease and slight random-looking (fixed) rotations; string draws with dash offset |
| 3 | Number chart | Bars/lines grow while values count up; the key bar in the accent | any comparison or trend; "X% of…" | `numberchart.html` | counters via onUpdate on a tweened object; registry `data-chart`, `bar-chart-race`, `mk-progress-stat` |
| 4 | Frame break | A framed picture, then the subject bursts past the frame edge | reveals, "this escaped/blew up", product hero | `framebreak.html` | with `hyperframes remove-background` the speaker's cutout can break the frame (z-order: frame < cutout) |
| 5 | Digital zoom | The camera snaps into a region of the footage, HUD sells it | demos (a setting, a line of code), reactions, emphasis | `digitalzoom.html` + `#cam` tween in index | animate the `#cam` wrapper, never the `<video>`; snap in fast (expo.out), drift, ease out |
| 6 | Phone mock-up | The thing on a phone in a device frame that tilts in; UI acts | apps, scam texts/DMs, settings walkthroughs | `phone.html` | perspective on the scene root; real screen recordings go in as a `<video>` inside the screen |
| 7 | Checklist | Boxes tick on the words that name them | the "what to do" beat, CTAs, recaps | `checklist.html` | ticks drawn with stroke-dashoffset; one row per spoken item |
| 8 | Headline wall | Many recreated headlines fill a wall; pull back for scale, push in on one | news, "everyone's talking about", proof of scale | `headlinewall.html` | recreated cards only (outlet name in small text, never logos/screenshots); verify every headline |
| 9 | Zoom-through cut | An on-screen object grows past the frame and becomes the next scene | chapter changes, "here's how it works", hook → body | `zoomthrough.html` | press (scale 0.92), then scale ~26× with power3.in; next scene enters blurred and sharpens |
| 10 | Spotlight | The frame dims except a pool of light on the detail | "look at this" in footage or UI, the giveaway in a scam | `spotlight.html` | radial-gradient mask driven by CSS variables from a tweened object |
| 11 | Doodle board | Hand-drawn circle/arrow/underline and a scribbled note | annotating footage/UI, casual explainer energy | `doodle.html` | SVG paths drawn with dashoffset; marker font (Caveat, Permanent Marker); note revealed in steps |
| 12 | Cover story | The frame becomes a magazine cover around the speaker | big-story hooks, thumbnails/covers, series openers | `cover.html` | masthead in a display serif, issue line, cover lines left/right of the face, barcode |
| 13 | Paper cut | Torn-paper layers with real shadows in stop-motion steps | playful explainers, history, "cut & paste" topics | `papercut.html` | `steps(n)` eases for 8–12 fps feel; jagged SVG edges; drop-shadow filters on decorative layers |
| 14 | Glass type | Frosted glass over the footage, big type, a sheen passing | premium/tech moments, quotes, key claims | `glass.html` | `backdrop-filter` blur + a DARK base (rgba(15,16,22,.4–.78)) so it never goes white on white |

More building blocks: the HyperFrames registry (`registry/blocks`, `registry/components` in
github.com/heygen-com/hyperframes: ~450 items: kinetic type, caption styles, maps, charts, glitch, grain, camera shake,
transitions, lower thirds, social cards). Add new techniques to this table when references show them working.

## How a technique earns a place in a storyboard
1. **Video type** fits (news explainer, demo/how-to, opinion/hot take, list, story).
2. **The beat** needs it (hook, proof, explain, turn, payoff, CTA, outro). One technique per beat; 3–6 different ones per Reel.
3. **Evidence**: it appears in top-performing Reels of the same type (scoreboard), or in a reference Swati sent.
4. **Readability on a phone**: the review-phone sheet stays legible; the face isn't buried for long.

## Evidence scoreboard (from references/*: fill as references are analysed)
Ranked by views; likes and comments shown; saves are never public and shares rarely are, so they're not used.

| Technique | Seen in (reference names) | Median views | Median like rate | Video types | Notes |
|---|---|---|---|---|---|
