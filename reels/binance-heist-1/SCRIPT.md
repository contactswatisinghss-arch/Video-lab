# Binance heist, Part 1: how it was done (v3, reference-based)

See REFERENCES.md. One line per beat, 165 wpm, no dates on screen.

```
Binance lost 6 billion. No code was broken.
Let me show you how.
It's Binance, the world's biggest crypto exchange.
Step one: one DevOps engineer's laptop.
From there, the attacker reached the system that sends withdrawals.
But Binance says its keys were never stolen.
So how do you rob a bank without the keys?
Step two: the trap.
On Ethereum, a wallet can run instructions on its own,
like a standing order at your bank.
The attacker wrote one for a Binance hot wallet.
Send every coin you hold to me.
Step three: the timing, and this is the clever part.
Each Ethereum transaction needs the next serial number,
like the token number in a queue at the bank.
On a wallet this busy, that number never stops moving.
So they pre-signed 50 requests. One matched.
That one transaction moved about 2.5 billion dollars.
In total, 6.3 billion left across 10 blockchains,
most of it in 20 minutes.
And the trap lived on the blockchain,
so locking the attacker out of Binance's servers didn't stop it.
Investigators link it to TraderTraitor, a North Korean group.
North Korea denies it.
If you lead a tech team, here's the real lesson.
A laptop login should never add up
to the power to move 6 billion dollars.
Part 2: how 3 billion of it got frozen,
when crypto supposedly can't be.
Follow, because this 6 billion story isn't over.
```

## Scores
- Hook (hookscore.py): 88.0 STRONG
- Beats (beats.py --wpm 165 --target 80): 238 words, 86.5 s, no beat over 4 s, loop on "6 billion", no flags
- Human (detect.py): 76.2 PASS

## Sources
- Gizmodo: https://gizmodo.com/how-hackers-stole-6-3-billion-from-binance-in-minutes-2000833158
- Yahoo Finance: https://finance.yahoo.com/markets/article/bitcoin-drops-to-76000-as-binance-hack-spooks-investors-tether-circle-freeze-assets-083406383.html
