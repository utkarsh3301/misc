# Strategy 4: Supertrend trend follower gated by ADX/DMI

## Specification

Supertrend(10, 3) on 5 to 15-minute bars of the near-month future or
spot. Enter on a Supertrend flip confirmed by 5-minute ADX above 20-25
and the directional index (+DI/-DI) agreeing with the flip direction.
Exit on the next flip or a hard stop of about 25% of premium; no fixed
target, since a trend system earns its keep in the tail of a move.
Square off by 15:10, cap at 2-3 trades per day.

`strategy.py` implements this on whatever bar interval it is given; the
demo uses 1-minute bars for simplicity, which produces more (noisier)
flips than the intended 5-15 minute timeframe would in practice.

## Evidence

Standalone daily-bar studies put Supertrend's win rate around **40-43%**
consistently: a Nifty 500 daily study (2012-2025, parameters 3-21
periods x 1-3 multiplier) found 40-43% across all parameter sets;
Liberated Stock Trader found 42-43% across 4,052 trades with low
standalone expectancy.

The more relevant intraday evidence is an independent Indian study on
GitHub (nifty-banknifty-intraday-trend-algo): on 15-minute Nifty bars,
32 trades over 60 days, **gross profit factor 1.55, falling to 1.27
after statutory charges alone, to 1.01 at 2 bps slippage, and to 0.82 at
4 bps**. The same logic on 5-minute bars lost 19-23% over 60 days on
both indices. On 15 years of daily bars it showed profit factor 1.10 on
Nifty and 1.92 on Bank Nifty. The author's read: sound entry logic, but
a friction-and-runway problem at intraday speed. Treat vendor claims of
50-55%+ win rates on 5-minute data as unverified.

## Probability of profit

Monte Carlo assumption: **41% win rate**, avg win 36.5 points / avg
loss 20 points (reproduces the GitHub study's pre-slippage profit
factor of 1.27: 0.41x36.5 / 0.59x20 = 1.27). Result: POP over 250
trades is around 73% at 1 lot. Net profitability depends on keeping
your real slippage under roughly the 2 bps-equivalent threshold where
the cited study's edge started to erode; measure this before sizing up.

## Data requirements

5-minute OHLC is enough (from any broker, with historical data
available); this is the least latency-sensitive strategy in the set,
with roughly one signal per hour at most.

## Option-buying considerations

Holding periods of 30-120 minutes carry real theta; prefer ITM strikes
and avoid running this on expiry day, where gamma-driven premium moves
overwhelm the trend signal. Supertrend flips lag, so a meaningful part
of any move is given back at exit; consider a partial exit at +1.5R if
you build this out further.

## Failure modes

Sideways days with repeated flips are the primary killer, followed by
gap-then-fill opens and event-driven spikes. Monthly-only Bank Nifty
options (since Nov 2024) have wider spreads away from ATM; stay near
the money.

## Sources

github.com/anirudhatalmale6-alt/nifty-banknifty-intraday-trend-algo.
Liberated Stock Trader Supertrend study. Nifty 500 daily Supertrend
parameter sweep (Share.Market backtest writeup).
