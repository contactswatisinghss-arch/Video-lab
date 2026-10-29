# plan.json guide (engine 1.0)

One `reels/<slug>/plan.json` per Reel. **Every time is a second on the RAW video**, exactly as in
`reels/<slug>/transcript.json` (word `s` = start, `e` = end). The engine cuts pauses and maps raw
seconds onto the final timeline itself, so take `at` / `start` / `end` straight from word times.

Check a plan without video: `python3 -m engine.reel sheet --plan reels/<slug>/plan.json --out sheet.jpg`
(needs `transcript.json` + `meta.json` next to the plan). Pushing `plan.json` to `main` starts the full render.

## Top level

| key | what | default |
|---|---|---|
| `style` | `briefing` (night/cyan/violet, red threats, green fixes) or `demo` (mint + orange accents) | `briefing` |
| `palette` | override colours, e.g. `{"cyan": "#5BE7C4"}` | – |
| `brand` | `{"tag": "SWATI TALKS TECH", "tag2": "BRIEFING", "part": "PART 1/2"}`; `part` optional | none |
| `cuts` | `max_pause` (0.4 s), `pad` (0.1 s), `keep_tail` (`true` = keep to the end for the end card, or seconds), `keep_head`, `remove: [[a,b],...]` raw ranges to cut (retakes, flubs, false starts) | |
| `punch_ins` | raw seconds; the shot containing each gets a hard 1.15× punch-in (hook, reveals) | `[]` |
| `zooms` | demos: `[{"start","end","rect":[x,y,w,h]}]`, rect = fractions of the (vertical) frame to crop into | `[]` |
| `captions` | `fixes: [["heard words","Correct"]]` (multi-word merges), `red: [...]` risk phrases, `green: [...]` fix phrases (one boxed per line), `max_words` 4, `max_chars` 24, `hide: [[a,b]]`, `case: "upper"` | |
| `audio` | `{"loudnorm": true}` → −14 LUFS (Instagram level) | on |
| `cover_at` | final-timeline second for `cover.jpg` (pick a frame with the hook title on screen) | 1.2 |
| `fps` | 30 (60 doubles render time) | 30 |
| `scenes` | list of scene objects (below), ordered by time; don't overlap two big top-third scenes | |
| `post` | `{"caption": "...", "hashtags": ["#..."]}` → `caption.txt` attached to the release | |

Layout rules baked into the templates: brand row at y≈196, graphics in the top ~45 % (y 250–1000),
captions centred at y=1340 (70 %), nothing below ~1500 (Instagram UI). Face stays visible mid-frame.

## Scene types (all need `type`, `start`, `end`; inner `at` times are raw seconds)

**Hooks**
- `hook_globe` – glitch-in title over a turning wireframe globe with red pings. `title: [["BLACK","white"],["OCTOBER","red"]]`, `kicker`, `title_out` (raw s the title glitches away), `pings: [{lat,lon,at}]`, `lon_start`, `spin` (deg/s).
- `hook_title` – glitch-in stacked title, no globe. `title`, `kicker`.

**Data / proof**
- `stat_meter` – tilted sticker counting up + optional meter. `sticker: {value, suffix, label, color, at, count_up}`, `meter: {label, value, max, tag, at}`.
- `news_cards` – label pill + stacked paper headline cards. `label: {text, color}`, `cards: [{outlet, date, headline}]`, `at`, `step`. Recreated styling only: no logos, no screenshots. Verify every headline.
- `callout_card` – one icon card. `icon`, `kicker`, `text`, `color`, `y` (default 330).

**Place**
- `globe_pins` – globe turns to each pin as it is named. `pins: [{name, lat, lon, at}]`, optional `turns: [[raw_s, centre_lon], ...]`, `callouts: [{start, end, icon, kicker, text, color}]` (shown under the globe).

**Explain**
- `title_chip` – mono name chip + subtitle + red tag pills. `title`, `subtitle`, `tags` (e.g. CVE IDs).
- `stack` – layer diagram. `layers: [{icon, label, note, fill}]` (fill `night`/`violet`/...), `crack: {layer, at, tag}`, `all_red_at`, `callouts`.
- `login_breach` – sign-in box, fields struck, stamp, impact rows. `title`, `fields`, `strike_at`, `tag`, `stamp: {at, text: [..]}`, `list_at`, `items: [{at, icon, text}]` (max 4).
- `icon_list` – titled list ticking on. `title`, `color`, `items: [{at, icon, text}]` (max 5).
- `hero_row` – analogy: hero icon glides in, row of items open. `label`, `hero_icon`, `item_icon` (`house` has doors), `count`, `hero_at`, `open_at`, `step`.
- `timeline` – dated vertical timeline. `header`, `items: [{at, icon, date, text, color}]` (max 7), `alert_at` (line turns red), `alert_index` (pulsing node).

**Fix / action / close**
- `status_tiles` – title + tiles flipping to a status. `title`, `subtitle`, `icon`, `count`, `flip_at`, `step`, `flip_label`, `flip_color`.
- `shield_versions` – shield + big word + chips. `title`, `subtitle`, `chips`, `color`.
- `checklist` – action card with ticking rows. `title`, `kicker`, `rows: [{text, sub, at}]` (max 4), `color`.
- `end_card` – series cliffhanger. `kicker`, `title: [lines]`, `sub`, `tiles: [icons]`, `follow`, `handle`. `end` optional.

**Demo helpers**
- `highlight` – pulsing outline on screen content. `rect: [x, y, w, h]` in FINAL frame pixels (1080×1920), `label`, `color`.
- `lower_third` – name strap at y≈1150. `title`, `sub`.
- `text_card` – plain text box (ASS). `text` (`\n` new line, `{red}`/`{green}`/`{cyan}`/`{violet}` … `{/}` colour runs), `style` `Card`/`Mono`/`Title`, `y`.

Colours: `white`, `red` (threat only), `green` (fix only), `cyan`, `violet`, `amber`, `grey`, or `#hex`.

Icons: building, card, fridge, shield, shield_check, lock, lock_open, code, terminal, power, folder, key, server,
browser, globe, hourglass, chip, wrench, calendar, drop, video, bolt, house, alert, user, cloud, eye, chart, mail,
phone, bug, link, search, check, cross, wifi, money.

## Rules
- Every graphic carries information. Icons and diagrams only, never anything that looks like real attack commands or tooling.
- A new visual beat every 4–6 s; graphics change on the spoken word they illustrate (use word `s`).
- Facts on screen must be verified (numbers, dates, versions, CVE IDs, headlines). If unsure, leave it off.
- Reference example: `docs/examples/black-october.plan.json`.
