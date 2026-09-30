# Strategy 7: Volatility-regime-gated squeeze breakout

The regime gate here is recommended as a global filter across all seven
strategies, not just this one.

## Specification

**Regime gate (`strategies/common/regime_gate.py`):** no new trades of
any strategy when ATM IV or India VIX is in the top 20-25% of its
1-year range, unless realized volatility is also expanding; skip the
day before and of RBI policy, Budget, major CPI and Fed decisions, when
IV crush risk is highest. Prefer trading when IV rank is in the bottom
half (options relatively cheap).

**Squeeze breakout (implemented in `strategy.py`):** on 5-minute bars,
detect Bollinger Bands (20, 2) narrower than their own 20th percentile
and sitting inside Keltner Channels (20, 1.5xATR): a volatility squeeze.
Buy a call on the first close above the upper band after a squeeze, with
volume above 1.5x its median; buy a put on the mirror condition. Stop on
a close back inside the midline or a 20% premium stop, trail on the
opposite band edge, time stop 60 minutes, flat by 15:10.

## Why the gate matters, and why the entry is a hypothesis

Implied volatility carries a negative variance risk premium on average
(options tend to be priced above what subsequently realizes). Nifty
options specifically show negative overnight and positive intraday
returns (Papagelis et al., *Journal of Futures Markets*, 2025), which is
theoretical support for never carrying long premium overnight and for
avoiding buying options right before IV-crushing events. That part of
this strategy is evidence-backed.

**No rigorous, post-cost published Nifty backtest of the squeeze
breakout entry itself was found.** Practitioner use of Bollinger/Keltner
squeezes is widespread but the win rate is not independently verified
for this market. Treat the entry as a hypothesis to test on your own
data, and the IV/event gate as the well-grounded part worth applying to
every other strategy in this repo too.

## Probability of profit

Monte Carlo assumption: **40% win rate**, avg win 33 points / avg loss
15 points, matched to the breakout profile seen in the other breakout
strategies in this set (24-49% win rates across the US and India
evidence cited for Strategies 3 and 6). Result: POP over 250 trades is
around 96% in the simulation, but this leans entirely on an unverified
win-rate assumption for a strategy with no direct backtest; treat this
number with more skepticism than Strategy 3's, which has real Zerodha
data behind it.

## Data requirements

5-minute OHLCV for the future. India VIX (published) or your own ATM IV
computed via Black-76 from option mid-prices; a stored daily IV history
if you want a real IV-rank calculation rather than the placeholder in
`regime_gate.py`.

## Failure modes

False breakouts from lunch-hour squeezes that never expand. Squeezes
that resolve via an overnight gap, which an intraday-only strategy is
forced to miss. Event-driven expansions, which the gate is specifically
designed to blackout, so expect this strategy to sit out some of the
market's larger moves by design.

## Sources

Papagelis, et al., *Journal of Futures Markets* (2025), Nifty options
overnight/intraday return study. General squeeze-breakout mechanics are
standard technical-analysis practice; no single authoritative backtest
source for the India-specific case was found in this research pass.
