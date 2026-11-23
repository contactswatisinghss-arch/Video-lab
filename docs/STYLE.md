# Swati Talks Tech: living style notes

What we know works for this channel. Claude updates this file as reference Reels are studied and as posted
Reels report their numbers. These are guardrails and learnings, not a template: each Reel still gets its own look.

## HARD RULES from Swati (Nov 2026), these override anything below
- **The final keeps her shot exactly (12 Nov 2026): 4K 60p, original HDR colours, no grading, no change to any
  video-quality vital.** Only edit elements are added, laid over the original upload (docs/PIPELINE.md). "If I have to
  add anything on the quality I will explicitly ask you to do it or use a filter." Reference for "original" = her raw
  upload. Never use `"final": {"mode": "rerender"}` unless she asks.
- **Never change her footage's look**: no brightness, contrast, saturation, hue, white balance, colour overlays,
  face light, vignette or "grade" of any kind. `#base` gets no CSS filter and no blend layers over it.
- **Previews are drafts**: 1080p, tone-mapped (her "first colours"), for checking the edit only. Say so when sending one.
- **Captions and text NEVER cover her eyes or face (12 Nov 2026).** Locate her face from `frames.jpg` before
  placing captions. Her usual framing fills the frame (hair top ~430, eyes ~880, chin ~1440 px), so in room shots
  captions sit below the chin (~1480); when a news card sits in the top band, captions sit just under the card
  (~770) above her hair. Graphics in the top band must not overlap her head either. Check every beat on the preview
  sheet for this before sending it.
- **The cover must say what the Reel is about**: the topic name big and readable (e.g. "MIXTURE OF EXPERTS"), plus
  the hook. No mid-sentence caption on the cover frame. Show her a cover draft with the preview, before the final.
- **Never make her wait on a second round for an either/or (11 Nov 2026).** Whenever there's a choice (two
  openings, two looks), render BOTH versions at the same time so she only picks. Second edits of the same upload:
  a variant folder with `"release": "<slug>"` in edit.json (see `ci/variants.py`); variants share transcript + cutout.
- **No separate sound-effects version by default (12 Nov 2026).** Only the clean version (her voice). SFX is a
  later topic (she may bring a sound-effects skill); `ci/sfx.py` runs only for reels that have `sfx.json`.
- **Speed matters**: tell her the expected time at kick-off (~2 h raw upload to final + her review, see
  docs/PIPELINE.md) and report the real time when the final is out. Don't make her repeat a preference: turn every
  repeated request into a default here.
- **When she says "don't cut my audio"**: `cuts` = `{"max_pause": 99, "keep_head": 1.0, "keep_tail": 2.0, "remove": []}`, no `speed`.
- **No camera moves (`#cam` punch-ins/slides) by default**: they can't be laid over the 4K original yet and would
  force the old 1080p30 re-render. Put cards in the top band or behind her (`data-layer="under"`) instead.

## Series: AI Basics Before 2026 Ends (10 Reels, Nov 2026)
- Slugs `ai-basics-day-1` … `ai-basics-day-10`. Scripts live in Swati's doc; each opens with the topic in plain words
  in line 1 (her rule, 14 Nov 2026: the first 3 s must say what the Reel is about), then the surprise, then the
  "Day X of 10" badge. Continuity = the day number, not a character.
- **Background (14 Nov 2026):** she wants one series background, ideally a library. Her priority: "smooth background
  which doesn't look edited, more than having this exact background." Before deciding, show still-frame samples from
  the real Day 1 footage, all built at once: A = library plate (built from her library photo, softly blurred like
  Portrait mode) behind the cutout, with feathered hair edge + slight light wrap; B = her real room, gently defocused
  behind the cutout, with plants/lamp glow added in depth; C = real room, decor only on empty wall, no cutout. The
  china-ai-bubble cutout looked unnatural and the news Reel's cutout wasn't smooth: blur the plate and soften the
  matte edge; never a sharp plate behind a cutout. Her pick becomes the default for all 10 days.
- **Graphics matter a lot in this series (14 Nov 2026):** play with fonts, colours and highlights; strong graphics;
  cards swirling/orbiting around her. Keep it consistent across the 10 days (series identity) while each day's
  analogy gets its own visuals. Day badge + 10-dot progress bar in a fixed corner; board word recap card each day.

## Channel
- @swatitalkstech: tech explainers and news for a broad audience ("even if tech isn't your thing"); some demos.
- Tone: credible briefing, calm authority, no hype; one bold hook per video is fine.

## Identity anchors (keep across Reels so the page is recognisable)
- Swati on camera is the hero; graphics support her, they don't bury her.
- Captions: heavy sans (Inter 900 has worked), 2–4 words, word-by-word on the real timings, one key phrase per line highlighted.
- Meaning colours: red = threat/risk, green = fix/action. Other colours are free per Reel.
- Optional small handle tag; branding is not required on every frame.

## NvidiaScandal (12 Nov 2026): news-reaction, "genuinely talking", minimum edit
- She asked: no audio cuts, no grading, news backdrops (NYT story → stock drop → Democrats → Europe), real room otherwise.
- Built two versions at once: Preview 1 (her idea: news fills the background behind a cutout) and Preview 2 (Claude:
  real room, the shot slides down and recreated news cards sit in the top band). She chose **Preview 1**.
- It took ~9 h from upload to a usable final (colour rework, a broken HyperFrames update, duplicate runs), so she
  posted her own unedited 4K60 video instead. Lessons → pipeline v3 (docs/PIPELINE.md): final laid over the original,
  shared cutout, parallel jobs. The v3 final of Preview 1 (4K60 HDR, audio copied) was approved as quality-identical.
- Later feedback (14 Nov 2026): the cutout + background in that news Reel "wasn't smooth" (edges looked edited).

## NuclearFusion (11 Nov 2026): what she rejected and what she approved
- Picked look "A + C" from 3 sample covers: C = full-screen takeovers (sun dive, 100,000,000 °C counter, episode
  slam, plasma) she liked; A = plum solar-glass cards over her real room.
- **Rejected:** her face cropped into an oval/portal at the START ("looking odd"). The oval is fine later (plasma
  part, end card) but never on the opening. Also rejected the A glass title card as the opening.
- **Approved opening:** big glowing title (NUCLEAR FUSION) + keyword stickers on frame 0, full frame, then a
  headline flash (3 recreated news cards slap down, fly off), then a mini sun drops into her hand.
- She listens closely to the audio: flagged a doubled phrase ("they repel, they repel") and a clipped word
  ("researchers" heard as "archers"). Whisper mis-times stretched words; check joins around every cut and fix word
  times in transcript.json when a cut clips a word.
- Voice notes: she reviews on her phone and often replies by voice; offer frames she can see rather than descriptions.

## Gemini 4 Carbon (30 Oct 2026, auto-approved test run)
- Look: carbon-black frosted panels over her light wall; amber = locked/access. Techniques: glass type, orbit,
  double-edged split (new), access-list checklist, step cards, loader end card. Awaiting her stats.

## What Swati liked (Black October, Oct 2026)
- Caption timing and sync.
- Real graphics that carry information: news-style headline cards (recreated, never screenshots/logos), a severity meter, a globe with pins, a cracked "stack" diagram, a timeline turning red at the turning point, a shield + fixed versions, a Part 2 end card.
- She disliked: plain text cards, basic fonts, no visuals.

## MixtureOfExperts (Nov 2026): what she rejected and what she approved
- **Rejected (v2):** "seems repeat of all previous videos and looks monotonous with black screen and popped out words
  without visual aesthetic elements." So: no more dark/black top panels as the default, no word-by-word pop-in
  captions, and don't reuse the same card system Reel after Reel.
- **Approved (v3, "Mix A + C"), picked from 3 sample frames:**
  - A, storybook: bright illustrated sticker cards (cream card, white border, soft shadow, tiled kitchen wall) with
    original cute cartoon characters (8 chefs: sleeping vs glowing "cooking" states) for the analogy beats; Fredoka.
  - C, scrapbook: white/yellow marker doodles drawn on her real wall (draw-on strokes), handwritten notes (Caveat,
    clip-path write-on), torn yellow paper strips with tape, taped lined/graph paper for facts.
  - Captions: Fredoka 600, the whole line eases in together; spoken word tints yellow; key words get a highlighter swipe.
- Cover rejected: "doesn't even tell what the topic is" (hook card only, plus a mid-sentence caption). See HARD RULES.
- Keep "Welcome to my series, AI explained like you're 5" in every episode of the series.
- Next time: vary again (don't make storybook the new default); offer 2–3 sample frames of different looks before building.

## Swati's picked style references (8 Nov 2026: "the edit is becoming a bit boring")
She chose these herself, so they outweigh topic research for LOOK and PACE. references/style-01..04.
Instagram gave likes/comments but no views, so engagement below is likes + comments only.
- style-01 @emmyxtech (solid-state batteries, 42 s, 2.3K likes): a visual change every **1.7 s** (24 cuts). Mixes
  her talking head with a **physical prop demo** (clay + plastic disc to show "squeezing"), labelled 3D diagram
  cards, macro/lab cutaways, and a burst of 10 rapid cuts at 36 s. Small white caps captions, one phrase at a time.
- style-04 @soojintech (AI fundamentals, 58 s, 44.5K likes / 17K comments): **top-half inserts** every 2–4 s that
  cover the upper half of the frame while she stays visible below (her own web app, a city photo tilting in, an
  office photo, a cat-with-book "Bob the librarian" metaphor for RAG). Hook frame has **floating keyword stickers**
  (RAG, MCP, Tokens, Context Window…) in outlined pink type around her. Sentence-case white captions, one short line.
- style-02 @solocontent.studio (story structure breakdown, 117 s, 620 comments) and style-03 @itsmegkilgore
  (Claude edits my reels, 46 s, **48.8K comments vs 12.7K likes**): slower cuts (6–11 s) but a curiosity hook
  ("Why did 139,000 people watch…") and a **comment-keyword CTA** at the end ("Comment DEMO and I'll show you…").
  That CTA is what drives comments to 2–4× likes in 03 and 04.
- Common to all four: first word at 0.0 s, 3.4–3.9 words/s, speech 78–90% of the runtime (no dead air).

### What to change in Swati's edits
1. **Pace**: a new visual every 2–3 s on average (was a beat every 3–6 s). Mix of: graphic card, top-half insert,
   prop/object shot, quick-cut burst on the payoff line. (Punch-ins = camera moves: avoid, see HARD RULES.)
2. **Top-half inserts** as the default B-roll format (recreated UI, diagrams, photos she supplies or generated
   illustrations), sliding/tilting in, her face kept visible below. Never real logos or screenshots of news sites.
3. **Keyword sticker cloud** on the hook frame (the topic's 4–8 key terms popping in around her) = a strong thumbnail.
4. **One playful metaphor visual** per Reel (like "Bob the librarian cat"), so it isn't all diagrams.
5. **Lighter captions** to test: smaller, one short line, so the inserts carry the energy (A/B against Inter 900).
6. **Ask her to film one prop shot** when the topic allows (her hands showing an object) — cheapest "real" B-roll.
7. **Comment-keyword CTA** ending ("Comment X and I'll send you…") — only if she can deliver the DM (needs an
   auto-DM tool or manual replies); suggest it in the storyboard, don't add it silently.

## Rules
- Every graphic carries information. Icons and diagrams only, never anything resembling real attack commands or tooling.
- Facts on screen are verified (numbers, dates, versions, IDs, headlines). Sources go in the pinned comment.
- **No specific dates** in on-screen graphics, captions or the pinned comment (Swati, 30 Oct 2026): say "just announced",
  "this week" etc. so a Reel doesn't look stale later. (Gemini 4 Carbon Reel was left as is.) Exception (14 Nov 2026):
  the AI Basics series may say "Before 2026 Ends" / "2027" because she will post it before the year ends.
- Footage is mostly shot at home at night on a plain wall: vary the look per Reel (see "Backgrounds").

## Backgrounds (to keep Reels from looking the same)
- **No regrading or relighting of her footage at all (see HARD RULES).** Variety comes from graphics and decor only.
- Option per Reel, picked in the storyboard: (a) keep the real room as shot; (b) replace the wall
  behind her with a topic-specific scene via `hyperframes remove-background` (cutout layered over a designed
  background; scenes behind her get `data-layer="under"`; check hair edges in the preview); (c) "split" looks:
  footage in a frame/phone/screen over a designed set. Default: alternate, and never two replaced backgrounds back to back.
- **Swati's preference (30 Oct 2026): keep her real room, add set dressing** (plants, wooden slat wall, shelf, soft
  lamp glow) rather than swapping the background. Digital version: decor layered on the empty wall areas and
  frame edges; anything that would pass behind her uses the `remove-background` cutout so she stays in front.
  Must sit low-contrast and never compete with the top-band graphics.
  Try it on the next Reel's preview and show a before/after frame first.
- **Background replacement: DON'T by default (Swati, Nov 2026).** Tried on china-ai-bubble (cutout over a designed
  walnut-panelled set): she found it "very unnatural". Keep her real room; only subtle decor on empty wall
  areas that never passes behind her. `bg_remove` in edit.json stays available but is off by default; it's a
  per-video choice (NvidiaScandal Preview 1 used news backdrops behind her because she asked, and she chose it).
  Exception: the AI Basics series is testing a blurred library plate (see the series section), by her request.
- Keep it **dynamic**: a different combination every Reel from a growing set: neon sign on the wall (soft glow +
  realistic flicker-on at the start; text = channel name, a topic word, or a techie motif: `>_` prompt, `</>`, `{ }`, a branch-and-commits line, `git push`, `sudo`, circuit trace; Swati likes "git / techie" neon. Use original designs, never a company's actual logo),
  plants (corner, hanging, desk), wooden slat wall, shelf with gadgets, LED strip. Neon colour can
  echo the Reel's palette. Track which set was used per Reel in the results log so repeats are spaced out.

## Learned from references
- AI-bubble refs (Nov 2026): @misseatinggood 1.6M, 24% likes: dot-com flashback then "sound familiar?", cut every 1.4 s;
  @graceblakeley0 1.2M: "Remember 2008?" past-crash parallel; @michael__mezz 3M: "you might think this isn't your problem";
  @shigglegitter9000 1.1M: one take, no numbers. Steal: the past-crash parallel + a "this is your problem" turn.

## Results log
| Reel | Posted | Length | 24 h views | Avg watch | % to end | Shares | Saves | Follows | Note |
|---|---|---|---|---|---|---|---|---|---|
| MixtureOfExperts | | 80.9 s | | | | | | | storybook kitchen + scrapbook doodles |
| NuclearFusion | | 98.6 s | | | | | | | glowing title + headline flash opening; A glass cards + C takeovers; real room, no decor; clean + SFX versions |
| NvidiaScandal | 12 Nov (her unedited 4K60 version) | 78.6 s | | | | | | | edit came too late (9 h); she posted the raw; v3 4K final of Preview 1 approved for quality afterwards |
| Anthropic-ipo | | 58.9 s | | | | | | | market-paper cards, headline flash, B2B path diagram, honest stock line; research waived; upload→final 2 h 05 m |
