# Binance heist, Part 2: script (instagram-agent /ig-reel)

Spoken script, one line per beat. Pace 165 wpm. No dates on screen.

```
3 billion in stolen crypto just got frozen.
You were told that can't happen.
So what is crypto, really?
Money that only exists as records, like Bitcoin or Ether.
Those records live on a blockchain,
a shared ledger, like a Google Doc
copied across thousands of computers,
so nobody can quietly go back and edit it.
Every transfer is public, right there on Etherscan.
That's how firms like TRM Labs tracked the stolen money live.
Now here's what most people miss.
Bitcoin has no company behind it.
On the Bitcoin network itself, nobody can freeze it.
Stablecoins are different. USDT belongs to Tether. USDC belongs to Circle.
Those companies can freeze coins,
and together they froze about 2.4 billion.
So decentralized? Not quite.
Then there's Binance, holding the keys
for millions of people who never touch a blockchain.
Convenient. Also one giant target.
Bitcoin dropped about 5% that day.
So here's my question for any tech, from Bitcoin to ChatGPT.
Who holds the off switch? Tether? Binance? You?
Save this.
Next time someone says crypto can't be frozen, you'll know.
```

## Scores
- Hook (hookscore.py): 82.3 STRONG
- Beats (beats.py --wpm 165 --target 60): 25 beats, 65.8 s, no beat over 4 s, loop on "crypto, frozen", no flags
- Human (detect.py): 83.1 PASS (burstiness 83, specificity 100, slop 100, fingerprint 100, voice 71)

## Hooks considered
- 82.3 STRONG (shooting): "3 billion in stolen crypto just got frozen. You were told that can't happen."
- 80.8 STRONG: "You think crypto can't be frozen? Three billion just was."
- 64.8 OK: "Crypto can't be frozen. Except three billion dollars of it just was."

## Sources
- Yahoo Finance (Tether 1.567B + Circle 800M frozen; BTC about -5%): https://finance.yahoo.com/markets/article/bitcoin-drops-to-76000-as-binance-hack-spooks-investors-tether-circle-freeze-assets-083406383.html
- Gizmodo (about 3B frozen in total; SAFU covers users): https://gizmodo.com/how-hackers-stole-6-3-billion-from-binance-in-minutes-2000833158
