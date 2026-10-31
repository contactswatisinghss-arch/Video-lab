# Binance heist, Part 2: why crypto exists and where it falls short (v3)

One line per beat, 165 wpm, no dates on screen ("2008 crash" is history, not a posting date).

```
Crypto was invented so nobody could freeze your money.
3 billion just got frozen.
Start with a 20 dollar note in your hand.
If you hold it, it's yours.
Your bank balance is different.
It's just a number in a Chase or Barclays database,
which is why a bank can freeze it with one click.
After the 2008 crash, when banks got bailed out,
someone called Satoshi Nakamoto proposed Bitcoin.
Digital cash. No bank, no Visa, no PayPal in the middle.
Instead of one bank's database, there's a blockchain,
a shared ledger copied across thousands of computers.
Not even Bitcoin's creator can quietly edit it.
Your coins open with a private key.
Whoever holds it, holds the money.
So where does Bitcoin fall short?
Lose your key and the money is gone forever.
So most of us hand our keys
to an exchange like Binance.
Which means we rebuilt the bank.
One company. One giant target.
The 3 billion that got frozen? Mostly stablecoins.
USDT and USDC are digital dollars run by Tether and Circle.
And they froze about 2.4 billion.
Bitcoin itself can't be frozen like that.
That's the promise. And the risk.
So ask this about any tech, from Bitcoin to ChatGPT.
Who actually holds the keys? Tether? Binance? You?
Save this.
Next time someone says crypto can't be frozen, you'll know.
```

## Scores
- Hook (hookscore.py): 75.1 STRONG (first line is 3.3 s, 0.3 s over the timing tool's limit; the number lands in line 2)
- Beats (beats.py --wpm 165 --target 80): 225 words, 81.8 s, no beat over 4 s, loop on "crypto"
- Human (detect.py): 77.7 PASS

## Sources
- Yahoo Finance (Tether 1.567B + Circle 800M frozen): https://finance.yahoo.com/markets/article/bitcoin-drops-to-76000-as-binance-hack-spooks-investors-tether-circle-freeze-assets-083406383.html
- Gizmodo: https://gizmodo.com/how-hackers-stole-6-3-billion-from-binance-in-minutes-2000833158
