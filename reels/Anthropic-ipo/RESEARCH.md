# Anthropic-ipo · research (DRAFT, incomplete)

Status: fact-check done. Reference research (step 3 tracks A and B) WAIVED for this Reel only by Swati on
23 Nov (vidIQ out of credits, news moving fast). Storyboard evidence comes from STYLE.md / TECHNIQUES.md and
her own past results instead; say so in BRIEF.md.

## Video
61.1 s, 4K 60p HLG, one framing (bookshelf behind her, face mid-frame). Type: news explainer.
Swati's asks for the edit: news, stock rising, the B2B path, other companies' adoption.

## Hook (tool: pinned instagram-agent hookscore.py @ d03c56b; text heuristics, AUC 0.83 for weak vs real, 0.56 for hit vs miss)
| Opening | Score |
|---|---|
| "Anthropic just raised $81 billion. That's bigger than SpaceX." (start at w5, 1.14 s) | 61.2 OK |
| "With the biggest IPO in history, Anthropic just raised $81 billion…" (as spoken) | 50.0 OK |
| "…and it did it by selling AI to businesses, not to you." | 48.0 WEAK (too long) |
| "Most of Anthropic's employees are now millionaires." | 39.2 WEAK |
Editorial: cut w0–w4 (first 0.84 s; w0–w2 are squeezed into 0.18 s, prob 0.01–0.32) and put "BIGGEST IPO EVER"
on screen from frame 0, so the lost words are carried by the title.

## Fact-check of her spoken claims
| Claim (words) | Verdict | On-screen wording | Source |
|---|---|---|---|
| raised $81 billion (w7–w9) | TRUE: 980M shares at $83 ≈ $81.3B | "$81B raised" | Anthropic pricing release; Wikipedia IPO page |
| bigger than SpaceX (w11–w13) | TRUE: SpaceX's IPO raised ~$75B earlier this year | "$81B vs $75B" | Marketplace |
| record-breaking (w16–w17) | TRUE: largest IPO by proceeds | "Biggest IPO ever" | Marketplace; Wikipedia |
| most employees now millionaires (w18–w22) | ESTIMATE only: filings don't disclose holdings; models say thousands of ~5,300 staff; most can't sell yet | "Thousands of employee millionaires (on paper)" | Fortune; Inc. |
| Claude on Amazon, Google, Microsoft clouds (w83–w96) | TRUE: Bedrock, Google Cloud (Vertex/Agent Platform), Microsoft Foundry | three cloud tiles | Azure blog; Anthropic regional-compliance page |
| ~250 customers at $10M+ a year (w111–w121) | TRUE: S-1, trailing 12 months to 30 Sep | "~250 customers × $10M+" | TechCrunch on the S-1 |

## "Stock rising" beat · what the data allows
IPO price $83 → first trade $111.50 (+34%) → day-1 close $97.17 (+17%) → Friday close $88.91 (−8.5% on the day,
Nasdaq's worst week since 2020), still ~7% above the IPO price. Show the real path; label "still above IPO price".
A straight "rising" line would be false. Optional backers angle: Amazon ~14.6% and Google ~13.4% stakes
(final prospectus), paper gains estimated in the hundreds of billions; estimates differ by outlet, so on screen
only the stake percentages.

## B2B path (diagram material)
Businesses' own cloud (AWS / Google Cloud / Azure) → Claude inside it → built into their products, coding tools,
workflows → paid by usage/contract. S-1: 11,900+ customers at $100K+/yr, 1,900+ at $1M+, ~250 at $10M+;
includes every Fortune 10 company and over half of the Fortune 500.

## Named adoption (verified only)
- Cloud partners: Amazon, Google, Microsoft (her own words).
- Deloitte (Deloitte's own site: Claude-trained staff, Salesforce + Anthropic work), Accenture (Anthropic
  business group, ~30,000 staff trained), Salesforce (expanded partnership), Allianz (TechCrunch).
- Logos must not be used (house rule): name tiles in our own type only.
- S-1 lists no individual customer names; "every Fortune 10 company" is the strongest verified line.

## Reference research (tracks A and B): NOT DONE
- vidIQ: account out of credits (outlier searches refused).
- references/queue.txt runs need a push to main: this session's GitHub access is read-only (403).
- references/pages.md (1M+ pages watchlist) doesn't exist in this repo yet.
- Web search found long-form/news videos only (Bloomberg, CNBC, Yahoo Finance, YouTube explainers), no view counts.

## Sources
- https://www.anthropic.com/news/anthropic-prices-initial-public-offering
- https://en.wikipedia.org/wiki/Initial_public_offering_of_Anthropic
- https://www.marketplace.org/story/2026/11/19/anthropic-unseats-spacex-as-biggest-ipo-ever
- https://finance.yahoo.com/technology/live/anthropic-ipo-live-anthropic-stock-drops-after-first-day-of-trading-143300513.html
- https://financefeeds.com/anthropic-ant-stock-88-91-saturday-week-ahead-after-friday-low-tested-83-ipo-price-bull-97-bear-80/
- https://www.cnbc.com/2026/11/21/anthropic-ipo-tech-selloff.html
- https://techcrunch.com/2026/10/26/anthropics-ipo-filing-reveals-its-strategy-for-keeping-enterprise-customers-hooked/
- https://www.sec.gov/Archives/edgar/data/0002130357/000162828026067168/anthropicpbc-sx1.htm
- https://fortune.com/2026/11/19/anthropic-ipo-millionaire-employees-billionaire-early-hires-wealth-concentration-warning-dario-amodei/
- https://www.inc.com/moses-jeanfrancois/anthropic-ipo-create-thousands-millionaires-cant-cash-out-yet/91438035
- https://fortune.com/2026/11/19/anthropic-ipo-amazon-google-stake-windfall-nonvoting/
- https://azure.microsoft.com/en-us/blog/claude-in-microsoft-foundry-is-now-generally-available/
- https://claude.com/regional-compliance
- https://www.deloittedigital.com/us/en/news/news-coverage/2026/deloitte-salesforce-anthropic-claudeforce-agentic-front-office-experiences.html
- https://techcrunch.com/2026/01/09/anthropic-adds-allianz-to-growing-list-of-enterprise-wins
