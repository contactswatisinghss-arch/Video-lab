# MixtureOfExperts: storyboard

**Video type:** concept explainer (series: "AI explained like you're 5").
**Audience:** curious non-specialists and early-career techies who hear "MoE" everywhere but have never seen it explained.
**Angle:** big AI models don't wake their whole brain for every word. A head chef (the router) picks 2 of 8 chefs (experts) per token, so you get a big model's knowledge at a small model's running cost. The catch: you still need memory for the whole kitchen.
**Payoff:** "8 chefs ready, 2 cook", proven with a real model (Mixtral 8x7B: ~47B total, ~13B used per token).

## Hook
- Spoken (current footage): "Would you wake up an entire team of chefs just to make one sandwich?" → hookscore **33.7 (WEAK, under 50)**: no number, low stakes.
- Recommended 10 s re-record (in the kitchen, where the hook is already shot):
  - "Your AI only uses 13 of its 47 billion parameters. You should know why." (78.7)
  - "Would you wake up 8 chefs to make one sandwich? AI models don't." (75.0)
- Edit until/unless she re-records: frame 0 carries "**8** chefs. **1** sandwich?" plus a keyword sticker cloud (Experts, Router, Tokens, MoE, 47B, 13B), the thumbnail pattern from style-04.

## Length and cuts (raw 103 s → ~78 s)
- Cut "Welcome to my series called AI explained like you're five" (raw 9.4–12.86): shown instead as an on-screen series badge. Also lands on the location change (kitchen → room), so the jump is invisible.
- Cut the recap "So the model has a whole team of experts available, but only calls on a few for each piece of work" (raw 69.3–76.2): the ending says it again.
- Pauses > 0.3 s cut; speed 1.1× (her pace 2.7 words/s raw; her picked refs run 3.4–3.9 words/s).
- Caption fix: "Mistral model" → "Mixtral model" (the model is Mixtral 8x7B, made by Mistral AI).

## Look
- **Kitchen brigade**: warm charcoal panels (#12100E), cream type (#FFF6E9), **saffron = head chef / router** (#FFB547), **green = an expert that is cooking** (#2EE59D), slate = idle expert. Red only for the "enormous compute" meter (cost = risk role).
- Type: Bricolage Grotesque 800 (titles, a friendly menu-board feel), JetBrains Mono (labels), Inter 800 captions at 76 px, one short line (the "lighter captions" test from STYLE.md #5).
- Motion: cards drop into the top band (190–700 px) on expo.out, chef hats pop on back.out, lines draw on with dash offset; punch-ins on "sandwich", "eight", "only those two", "47", the payoff.
- **Room look:** her real room/kitchen, warm night grade + soft vignette, no background replacement (her rule). No neon this time: the top band is busy almost every second, a sign would compete.

## Beat table (pace: a new visual every ~2.5 s)
| Time (final) | Her words | Technique | What appears | Why |
|---|---|---|---|---|
| 0.0 | "Would you wake up... one sandwich?" | Keyword sticker cloud + punch-in | "8 chefs. 1 sandwich?" title, 6 stickers pop around her | style-04 hook frame (44.5K likes); frame 0 = thumbnail |
| ~3 | "Some AI models use a similar trick" | Kinetic line | "AI DOES THIS ON PURPOSE" | sets the stakes before the intro |
| ~6 | "Hi, I'm Swati, tech lead at AWS" | Lower third + series badge | Name tag; "AI explained like you're 5" badge | credibility; replaces the cut series line |
| ~8 | "Bigger AI models... every calculation?" | Top-half insert: grid + meter | 32 "parts" all light red, COMPUTE meter maxes, headline turns into "Grow it, but wake fewer?" | top-half inserts every 2–4 s (style-04) |
| ~16 | "One approach is called mixture of experts" | Glass type | Frosted title with sheen | premium key-term moment |
| ~19 | "Imagine a kitchen with eight chefs... just two" | Playful metaphor | 8 chef hats, head chef drops in, 2 hats go green: "8 CHEFS / 2 COOK" | one playful metaphor per Reel (STYLE.md #4) |
| ~24 | "Inside an AI model... called experts... our chefs, all inside one model" | Diagram build | Network section with 8 expert blocks E1–E8; hats land on them | maps the metaphor onto the real thing |
| ~33 | "Your sentence gets broken into tiny pieces called tokens" | Token split | "Explain mixture of experts" snaps into chips Ex·plain·mixture·of·experts | answers "what's a token" before it matters |
| ~38 | "Central to this architecture is a router... different pair" | Router diagram (5 sub-beats) | Router = head chef node; token arrives; 2 lines draw to E2+E6 (green); results combine "+" → "answer ✓"; next token picks E3+E8 | the core mechanism, one change every ~2 s |
| ~54 | "One real example is Mixtral... 13 billion for each token" | Number chart | Mixtral 8x7B: 47B bar fills, 13B green slice counts up | proof with a real, verifiable number |
| ~62 | "So your whole model... every job" | Checklist | ✓ Trained as one big model, ✓ Compute of a small one, ⚠ Memory still holds all 8 | honest trade-off = credibility |
| ~73 | "That's the benefit... next episode" | End card | "8 chefs ready. 2 cook." + "Follow for the next episode" | echoes the hook word for the loop; series reason to follow |

## Facts (on screen) and sources
- Mixtral 8x7B: 46.7B total parameters, 12.9B used per token; 8 experts; the router picks 2 per token at every layer. Source: Mistral AI, "Mixtral of experts" (mistral.ai/news/mixtral-of-experts). On screen as "~47B" and "~13B", matching her words. The 13B bar is drawn to scale (27.6%).
- Tokens = a word or part of a word: standard definition, illustrative split only (not a real tokenizer's output; labelled generically).

## Evidence notes (honest)
- Topic references: vidIQ had no credits this session; two YouTube Shorts searches are queued (`moe-yt`, `moe-simple-yt`) but YouTube often blocks the runner, so pacing and look follow Swati's own picked style references (style-01..04) rather than topic data.

## Flags for Swati
1. Hook scores 34: a 10 s kitchen re-record would beat any edit (options above).
2. Comment-keyword CTA (style-03/04 drive comments 2–4× likes) only if you can answer DMs: e.g. "Comment CHEF and I'll send you the next episode first".
3. The "trained for better / compute of a much smaller one" line is a little hard to follow by ear; the checklist card carries it on screen.
