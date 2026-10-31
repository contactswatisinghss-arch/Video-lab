# Binance heist, Part 1: how it was done (v4)

v4 changes (Swati): stakes in the first 5 s (biggest crypto heist, no guns, no code broken, North Korea link), then a 10 s explainer of what Binance is and why exchanges exist, then the steps. See REFERENCES.md.

STATUS: written on a voice call where the scoring tools can't run. Rescore (hookscore.py, beats.py --wpm 165, detect.py) before shooting. Target set by Swati: hook 95+.

```
The biggest crypto heist in history just happened.
No guns. No masks. Not one line of code broken.
6 billion dollars gone from Binance in about 20 minutes,
and investigators link it to North Korean hackers.
So how did they do it?
First, what even is Binance?
Crypto is digital money. You can't hold it,
but every transaction is recorded on a blockchain.
You could use it yourself,
but then you guard your own keys.
Lose them, and the money's gone.
So most people use an exchange like Binance.
It's basically a bank for crypto.
It holds the keys for you,
and keeps some coins in a hot wallet, ready for withdrawals.
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
In total, 6.3 billion left across 10 blockchains.
And the trap lived on the blockchain,
so locking the attacker out of Binance's servers didn't stop it.
The group is called TraderTraitor.
North Korea denies it.
If you lead a tech team, here's the real lesson.
A laptop login should never add up
to the power to move 6 billion dollars.
Part 2: how 3 billion of it got frozen,
when crypto supposedly can't be.
Follow, because this 6 billion story isn't over.
```

## Sources
- Gizmodo: https://gizmodo.com/how-hackers-stole-6-3-billion-from-binance-in-minutes-2000833158
- Yahoo Finance: https://finance.yahoo.com/markets/article/bitcoin-drops-to-76000-as-binance-hack-spooks-investors-tether-circle-freeze-assets-083406383.html
