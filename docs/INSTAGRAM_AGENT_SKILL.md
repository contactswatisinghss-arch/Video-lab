---
name: instagram-agent
description: Swati's Instagram toolkit (Jake Schincariol's MIT instagram-agent-skill, 13 modes) for hooks, captions, humanizing, viral research, weekly plans, audits, profile, carousels, stories, comments, replies, DMs, repurposing. Use for /ig-* commands or any Instagram growth/writing request.
---

# Instagram agent (13 modes) · Swati Talks Tech

Wraps the open-source pack https://github.com/Jakeschincariol/instagram-agent-skill (MIT, by Jake Schincariol),
reviewed 31 Oct 2026: it only drafts text, never logs in, never posts; its 5 Python tools are offline (no network).

## Load it (every session; the sandbox can clone public GitHub repos)
```bash
IG=/tmp/ig && [ -d $IG ] || git clone -q https://github.com/Jakeschincariol/instagram-agent-skill $IG
cd $IG && git checkout -q d03c56bb598be770c60b201f94237e5d1a4268a6   # the reviewed version
```
If a newer commit is wanted, read the diff of every SKILL.md and .py first, then update the pinned hash here.
Run tools from their folder with `python3 -I` (e.g. `cd $IG/skills/ig-reel && python3 -I hookscore.py hooks.txt`).

## Route the request to a mode, then follow that mode's SKILL.md exactly
| Command / ask | Mode file |
|---|---|
| /ig-reel: hooks, script, beat sheet before shooting | skills/ig-reel/SKILL.md (+ hookscore.py, beats.py, hooks.json) |
| /ig-caption: caption + linter | skills/ig-caption/SKILL.md (+ caption.py) |
| /ig-human: de-AI any text | skills/ig-human/SKILL.md (+ humanize.py, detect.py, slop.json) |
| /ig-viral: what's working in her niche, swipe file | skills/ig-viral/SKILL.md (+ swipe.py) |
| /ig-plan: the week | skills/ig-plan/SKILL.md |
| /ig-audit: post-mortem from her insights | skills/ig-audit/SKILL.md |
| /ig-profile: profile score /100 + rewrites | skills/ig-profile/SKILL.md (+ rubric.json) |
| /ig-carousel, /ig-story, /ig-comment, /ig-reply, /ig-dm, /ig-repurpose | skills/ig-<name>/SKILL.md |

## Swati-specific adaptations (these override the pack where they differ)
- **State lives in the Video-lab repo, not ~/.claude** (sessions here don't keep files): wherever a mode says
  `~/.claude/instagram/<file>`, read/write `instagram/<file>` in `swatitalkstech-cell/Video-lab` via the GitHub
  connector (`voice.md`, `swipe.md`, `log.md`, `plan.md`). Fetch before running, push after.
- **Voice:** `instagram/voice.md`. If gaps are marked TODO, fill them from her transcripts (`reels/*/transcript.txt`)
  and ask her only for what can't be inferred (positions, proof, keyword CTA).
- **Channel rules from docs/STYLE.md apply:** no specific dates on screen, in captions or pinned comments; facts
  verified with sources; calm credible tech-briefing tone; max 5 hashtags (the pack agrees).
- **Her workflow is film-first:** /ig-reel is for planning the next video before she records (hook options scored,
  beat sheet at ~150 wpm, her measured pace). For an already-shot video, use hookscore.py to judge which of her
  spoken lines should open the edit, and hand captions to the talking-head-reel-editor skill's packaging step.
- **/ig-viral:** Instagram can't be scraped; use the browser only with Swati present in her own logged-in session,
  or YouTube Shorts data (the pack's yt-dlp method; Video-lab's `references/queue.txt` runs it on GitHub). Feed
  the outlier results into the reel editor's evidence scoreboard (docs/TECHNIQUES.md).
- **Nothing is posted, liked, followed, commented or DMed by Claude.** Every mode ends with a copy-ready block.
- Be honest about limits the pack states: the hook scorer kills weak hooks (AUC 0.83) but doesn't pick winners
  (AUC 0.56); the humanizer's checks are local heuristics, not detector verdicts.
