# Swati Talks Tech: living style notes

What we know works for this channel. Claude updates this file as reference Reels are studied and as posted
Reels report their numbers. These are guardrails and learnings, not a template: each Reel still gets its own look.

## Channel
- @swatitalkstech: tech explainers and news for a broad audience ("even if tech isn't your thing"); some demos.
- Tone: credible briefing, calm authority, no hype; one bold hook per video is fine.

## Identity anchors (keep across Reels so the page is recognisable)
- Swati on camera is the hero; graphics support her, they don't bury her.
- Captions: heavy sans (Inter 900 has worked), 2–4 words, word-by-word on the real timings, one key phrase per line highlighted.
- Meaning colours: red = threat/risk, green = fix/action. Other colours are free per Reel.
- Optional small handle tag; branding is not required on every frame.

## Gemini 4 Carbon (30 Oct 2026, auto-approved test run)
- Look: carbon-black frosted panels over her light wall; amber = locked/access. Techniques: glass type, orbit,
  double-edged split (new), access-list checklist, step cards, loader end card. Awaiting her stats.

## What Swati liked (Black October, Oct 2026)
- Caption timing and sync.
- Real graphics that carry information: news-style headline cards (recreated, never screenshots/logos), a severity meter, a globe with pins, a cracked "stack" diagram, a timeline turning red at the turning point, a shield + fixed versions, a Part 2 end card.
- She disliked: plain text cards, basic fonts, no visuals.

## Rules
- Every graphic carries information. Icons and diagrams only, never anything resembling real attack commands or tooling.
- Facts on screen are verified (numbers, dates, versions, IDs, headlines). Sources go in the pinned comment.
- **No specific dates** in on-screen graphics, captions or the pinned comment (Swati, 30 Oct 2026): say "just announced",
  "this week" etc. so a Reel doesn't look stale later. (Gemini 4 Carbon Reel was left as is.)
- Footage is mostly shot at home at night on a plain wall: vary the look per Reel (see "Backgrounds").

## Backgrounds (to keep Reels from looking the same)
- Option per Reel, picked in the storyboard: (a) keep the real room, regraded/relit per topic; (b) replace the wall
  behind her with a topic-specific scene via `hyperframes remove-background` (cutout layered over a designed
  background; ~2 fps on CPU, check hair edges in the preview); (c) "split" looks: footage in a frame/phone/screen
  over a designed set. Default: alternate, and never two replaced backgrounds back to back.
- **Swati's preference (30 Oct 2026): keep her real room, add set dressing** (plants, wooden slat wall, shelf, soft
  lamp glow) rather than swapping the background. Digital version: decor layered on the empty wall areas and
  frame edges; anything that would pass behind her uses the `remove-background` cutout so she stays in front.
  Must match the room's warm night lighting, sit low-contrast, and never compete with the top-band graphics.
  Try it on the next Reel's preview and show a before/after frame first.
- **Background replacement: DON'T (Swati, Nov 2026).** Tried on china-ai-bubble (cutout over a designed walnut-panelled set):
  she found it "very unnatural". Keep her real room; at most a warm grade + vignette, and only subtle decor on empty wall
  areas that never passes behind her. The `bg_remove` option in edit.json (ci/bgjobs.py) stays available but is off by default.
- Keep it **dynamic**: a different combination every Reel from a growing set: neon sign on the wall (soft glow +
  realistic flicker-on at the start; text = channel name, a topic word, or a techie motif: `>_` prompt, `</>`, `{ }`, a branch-and-commits line, `git push`, `sudo`, circuit trace; Swati likes "git / techie" neon. Use original designs, never a company's actual logo),
  plants (corner, hanging, desk), wooden slat wall, shelf with gadgets, warm lamp glow, LED strip. Neon colour can
  echo the Reel's palette. Track which set was used per Reel in the results log so repeats are spaced out.

## Learned from references
- AI-bubble refs (Nov 2026): @misseatinggood 1.6M, 24% likes: dot-com flashback then "sound familiar?", cut every 1.4 s;
  @graceblakeley0 1.2M: "Remember 2008?" past-crash parallel; @michael__mezz 3M: "you might think this isn't your problem";
  @shigglegitter9000 1.1M: one take, no numbers. Steal: the past-crash parallel + a "this is your problem" turn.

## Results log
| Reel | Posted | Length | 24 h views | Avg watch | % to end | Shares | Saves | Follows | Note |
|---|---|---|---|---|---|---|---|---|---|
