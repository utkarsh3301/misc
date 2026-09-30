# Strategy 2: VWAP trend (primary) with VWAP reversion (secondary)

## 2A: VWAP trend (implemented)

Trade in the direction of a 1-minute close crossing session VWAP,
computed on the near-month future (spot has no volume, so spot VWAP is
meaningless). To avoid flipping on every touch, require the close to be
beyond a band (0.15x ATR(14) here) past VWAP, with the VWAP slope over
the last 15 minutes agreeing with the trade direction.

Exit on a close back across VWAP or its band, a hard stop of about
20-25% of premium, or the session time stop (15:10).

## 2B: VWAP reversion (not implemented, spec only)

In a range regime (5-minute ADX below ~18, flat VWAP slope), fade a
close that moves 2 standard deviations from VWAP back toward it, target
VWAP, stop at 3 standard deviations. Needs a working regime detector on
top of what is in `strategy.py`; left as a spec since standalone
evidence for it is thinner than for 2A.

## Evidence

The core published result is Zarattini & Aziz (SSRN 4631351), QQQ,
Jan 2018-Sep 2023, 1-minute bars: $25,000 grew to $192,656 net of
commission, Sharpe 2.1, max drawdown 9.4%, from about 22,000 trades at a
**17% hit ratio with winners about 5x losers**. A QuantConnect
replication reproduced the 16% win rate but not the headline returns;
a later assessment concluded that "out-of-sample and after realistic
spreads it looks a lot less exciting than the headline numbers," and the
original authors later described VWAP as a source of alpha rather than
a standalone system.

No rigorous, post-cost Nifty or Bank Nifty backtest of this was found.
Algotest's VWAP option-buying template (applied to the option premium
directly, not the future) reported it underperformed a competing
straddle strategy overall, while outperforming during March-April 2022.
A lower-quality source (IJCRT paper, 53 demo trades, no costs or
drawdown reported) claims 65% accuracy and should be discounted.

## Probability of profit

Monte Carlo assumption: **30% win rate, winners about 5x losers**
(avg win 30 points, avg loss 6 points), a conservative read of the
Zarattini & Aziz payoff shape. Result: POP over 250 trades is high
(~100% in the simulation) because the payoff asymmetry does the work,
but this is unproven in India post-cost and the true win rate could be
meaningfully lower than assumed. Treat this as the most US-evidence-
dependent, least India-validated strategy in the set alongside Strategy
6.

## Data requirements

1-minute OHLCV for the near-month future (volume matters here, unlike
spot). Available from any broker WebSocket; minute history from Kite
for backtesting.

## Option-buying considerations

The trend variant suits long options well: few trades, few large
winners, quick exits on losers. The reversion variant fights theta and
should only be run (if built out) with ITM strikes and multiple lots to
overcome fixed costs on small moves.

## Failure modes

VWAP is unstable in the first 15-30 minutes; avoid signals before about
09:45. Low-volatility chop causes repeated whipsaw around VWAP, the
regime where replications underperformed most. Compute VWAP on the
future, not the option premium: option-premium VWAP is distorted by
theta decay, especially near Tuesday expiry.

## Sources

Zarattini & Aziz, SSRN 4631351. Bear Bull Traders "Magic of VWAP" and
the QuantConnect forum critique of it. Algotest VWAP option-buying
template (algotest.in/blog). IJCRT 2504775 (low-confidence source, used
only to illustrate the range of claims circulating).
