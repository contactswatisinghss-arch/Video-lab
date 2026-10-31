# Binance heist, Part 1: script (instagram-agent /ig-reel)

Spoken script, one line per beat. Pace 165 wpm. No dates on screen.

```
One laptop cost Binance 6 billion dollars.
You should know why.
It's Binance, the biggest crypto exchange in the world,
the place millions of people trust with their money,
and it says this started with one DevOps engineer's laptop.
From there, attackers got into a Binance hot wallet.
Then the clever part. They'd pre-signed 50 requests,
and only one had to work.
One did.
Most of the money was gone in 20 minutes,
across 10 blockchains.
About 6.3 billion. Four times Bybit's old record.
Investigators link it to TraderTraitor, a North Korean group.
Its favourite trick? Fake recruiters on LinkedIn.
Dream role. Coding test. Hidden malware.
We don't know if that happened here.
The code wasn't the weak point. Access was.
So if you lead a team, sit with this,
because if one laptop can move 6 billion dollars,
that's not a people problem, it's a system problem.
Job hunting? Never run a take-home test on your work laptop.
Part 2: how 3 billion got frozen.
Follow, because it all started with one laptop.
```

## Scores
- Hook (hookscore.py): 93.8 STRONG
- Beats (beats.py --wpm 165 --target 60): 23 beats, 63.6 s, no beat over 4 s, loop on "laptop", no flags
- Human (detect.py): 85.4 PASS (burstiness 100, specificity 100, slop 100, fingerprint 100, voice 71.9)

## Hooks considered
- 93.8 STRONG (shooting): "One laptop cost Binance 6 billion dollars. You should know why."
- 88.0 STRONG: "One engineer's laptop cost Binance six billion dollars, and you should know why." (4.7 s, too long)
- 50.6 OK: "Six billion dollars left Binance in about twenty minutes."

## Sources
- Gizmodo: https://gizmodo.com/how-hackers-stole-6-3-billion-from-binance-in-minutes-2000833158
- Yahoo Finance: https://finance.yahoo.com/markets/article/bitcoin-drops-to-76000-as-binance-hack-spooks-investors-tether-circle-freeze-assets-083406383.html
- Dark Reading (DPRK fake recruiters): https://www.darkreading.com/threat-intelligence/dprk-hackers-masquerade-as-tech-recruiters-job-seekers
