# NuclearFusion: research (step 3)

**Limits, stated plainly.** vidIQ was out of credits, and YouTube now blocks the GitHub runner's yt-dlp search
("Sign in to confirm you're not a bot"), so the existing `page-*-yt` searches failed and the new `fusion-*` queue
lines will probably fail too. This research comes from web search: view and engagement counts from public listings
(rosetta.to, socialpruf, lunarcrush, TikTok discover). No frames were analysed. Visual techniques are taken from
those listings plus each channel's well-known house style, and are marked *(house style)* where I couldn't see the
specific video. Saves and shares aren't public. Small sample: treat these as hints, not proof.
**Fix for next time:** add a `YTDLP_COOKIES` repo secret, or top up vidIQ credits.

## A. Topic virals (fusion / "artificial sun")

| # | Ref | Platform | Size | Views / engagement | Visual hook technique |
|---|---|---|---|---|---|
| 1 | Kurzgesagt: "Fusion Power Explained – Future or Failure" | YouTube | 1M+ page (~24M subs) | ~15M views | Flat-vector animated **sun cutaway → atoms colliding**: the mechanism drawn as an animation, no talking head *(house style)* |
| 2 | Thoughty2: "Fusion Energy is About to Unlock Humanity's Destiny" | YouTube | 1M+ page | 2.2M views | **Scale shock** in the first minute: the Sun burns 4.3 million tons of mass per second, "4 trillion Hiroshima bombs every second", over stock footage |
| 3 | Cleo Abram: "Nuclear Fusion, explained for beginners" + "We Tried To Do Nuclear Fusion" | YouTube / IG | 1M+ page (2.84M IG, avg ~1.65M impressions per IG post) | 910K and 860K | **Real hardware + prop**: building a fusor in a workshop, the glowing plasma shot as the payoff *(house style: real footage full-frame, "huge if true" optimism)* |
| 4 | @drbenmiles: "France breaks fusion world record" (WEST tokamak) | TikTok | 131K followers | 305K engagements; another fusion clip 963K engagements | **Record-number headline** + "XX times hotter than the Sun" comparison, talking head over B-roll of the reactor |
| 5 | @astrozcosmo (spacefever): how fusion reactors copy the Sun | TikTok | n/a | 77.3K likes, 1,181 comments | **Sun-to-reactor visual match** (the Sun, then the plasma ring) |
| 6 | WIRED: "MIT professor explains fusion in 5 levels" | YouTube | 1M+ page | 475K | **Analogy ladder** ("I put a star in a jar"), plasma as the 4th state of matter |
| 7 | China "artificial sun" Shorts / IG reels (EAST records) | YT Shorts / IG | various | IG posts 123K–194K views (fact-check study) | the phrase **"artificial sun"** + temperature number; note some viral ones used fake footage (a rocket launch) |

## B. Big tech/science pages (1M+): how they edit

- **Cleo Abram** (2.84M IG, 2.4M TikTok): recent shorts 2.0M–4.5M views ("This Metal Won't Sink" 4.5M, "5,000
  Spheres Under the Ice" 3.6M). Pattern: one big visual question in second 1, then full-screen real footage of the
  object, her face as the narrator in between; "Huge if true" optimism; ends on what it means for you.
- **Kurzgesagt** (fusion 15M): everything is a diagram that moves; the Sun is the recurring character; colour = meaning.
- **Thoughty2** (2.2M on fusion): scale comparisons as the hook (absurd numbers made physical).
- Swati's own picked style refs (docs/STYLE.md): @emmyxtech visual change every **1.7 s** + a **physical prop demo**;
  @soojintech **top-half inserts** every 2–4 s + **keyword sticker cloud** on the hook frame (44.5K likes);
  @itsmegkilgore **comment-keyword CTA** (comments 4× likes).

## What we'll steal (techniques, not content)

1. **The Sun as the opening visual**, matched into a reactor plasma ring (refs 1, 5, 7): a sun disc full-screen at
   frame 0 that collapses into a tokamak ring = "artificial sun".
2. **Scale-shock number** (refs 2, 4): one giant temperature/energy number counting up, with a "× hotter than the
   Sun's core" comparison bar.
3. **Mechanism animation** (ref 1): two atoms (H + H) colliding → helium + a flash of energy, drawn in SVG.
4. **Analogy ladder / "star in a jar"** (ref 6): the tokamak as a magnetic bottle (doughnut) holding a star.
5. **Record headline cards** (ref 4): recreated news-style cards, never screenshots or logos.
6. **Keyword sticker cloud** on the hook frame (style-04) for the thumbnail.
7. **Pace**: a visual change every ~2 s (style-01's 1.7 s), quick-cut burst on the payoff line.
8. **"What this means for you"** turn + **comment CTA** (style-03/04): only if Swati can reply to the DMs.

## Visual devices available (variety check: storyboard needs 5+)
full-screen takeover (sun), object-becomes-world transition (sun → plasma ring), kinetic number count-up, SVG
mechanism animation, top-half insert, recreated headline cards, keyword sticker cloud, punch-ins / jump cuts,
comparison bar chart, doodle annotation, checklist / "what's next" timeline, split screen (fission vs fusion).
