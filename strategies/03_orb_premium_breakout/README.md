# Strategy 3: Opening range breakout on the option premium

This has the strongest India-specific, post-cost evidence of the seven.

## Specification (Zerodha "In The Money" design)

At 09:16, pick the weekly Nifty CE and PE with premium closest to Rs
200 (typically ATM to ITM). Track each premium's own high/low over the
opening range window (09:15-11:15). Buy the CE when its premium closes
above its own opening-range high; independently, buy the PE on a close
below its own opening-range low. Stop loss at 20% of entry premium, no
fixed target, time exit before 15:15. Maximum 2 trades per day (one per
side).

`strategy.py` implements the opening-range breakout logic generically
(applied to the synthetic index proxy in the demo). In production, run
it on the actual CE/PE premium series, as the original study does, not
the index.

## Evidence

**Zerodha's own post-cost backtest** (Sandeep Rao, "The Long and the
Short", In The Money by Zerodha, 10 March 2026), Nifty weekly option
buying, Jan 2022-Feb 2026, net of brokerage, taxes and 0.2% slippage:
"a win rate of ~48% for an option buying strategy is not bad at all...
But the max drawdown of close to 45% is the number that demands
attention." Performance was smooth until around January 2024, then a
drawdown into 2025 that had not fully recovered by early 2026; 2026 so
far was "decent."

A separate spot-index test (IntradayLab, Nifty spot, 30-minute ORB, 2:1
reward:risk, Jul 2017-Mar 2026, no costs modelled): 2,122 trades, 48.7%
win rate, profit factor 1.23, +91.6% cumulative, max drawdown -11.2%,
8 of 9 years positive.

A 5-minute ORB replication on QQQ (Zarattini & Aziz) found a 24% hit
rate; an independent 2026 replication across five index CFDs reproduced
the gross edge but it vanished net of spread and was negative in
2015-2017. Small-sample claims (71.4% win rate on 42 trades) are too
small to trust.

## Probability of profit

Monte Carlo assumption: **48% win rate**, avg win 40 points / avg loss
30 points (this ratio reproduces Zerodha's cited profit factor of 1.23
at a 48% win rate: 0.48x40 / 0.52x30 = 1.23). Result: POP over 250
trades is around 80%, but expect the same 30-45% peak-to-trough
drawdown Zerodha's own test showed. **Size at a quarter to half of what
you'd otherwise use, precisely because the win rate is real but the
drawdown is large.**

## Data requirements

1-minute option OHLC for the selected strikes; a live option-chain
snapshot at 09:16 to pick the Rs-200 strikes. Order frequency (2 trades
per day) is trivial against rate limits.

## Option-buying considerations

The best-matched strategy in this set to long premium: few trades,
genuinely directional, winners allowed to run with no fixed cap. Rs 200
strikes reduce theta paid per unit of delta.

## Failure modes

Range-bound years (2023 in the spot data; 2025 in Zerodha's option
test). Double-breakout days where both CE and PE trigger and both stop
out. Gap-and-fade opens. Keep separate statistics for Tuesday expiry
days. Bank Nifty needs the opening range recalibrated: it is monthly-
only since the November 2024 weekly discontinuation, with a lot size of
30 and materially higher, lower-gamma premiums than the old weekly
regime most online content still describes.

## Sources

Sandeep Rao, "The Long and the Short", In The Money by Zerodha
(inthemoneybyzerodha.substack.com), 10 March 2026. IntradayLab Nifty
ORB backtest (intradaylab.com). Zarattini & Aziz, SSRN 4631351.
Sharekhan on the Nov 2024 weekly options discontinuation.
