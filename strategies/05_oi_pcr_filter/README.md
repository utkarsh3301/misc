# Strategy 5: Open interest build-up + PCR directional filter

## Why this is a filter, not a standalone strategy

The evidence for OI/PCR as a standalone directional signal is weak. A
2001-2013 Nifty study (Economies/MDPI) found PCR's predictive power
varies by time scale and is not a clean standalone edge. A Bank Nifty
study (Singh & Chaudhary, ICFMCF 2023) found option OI and volume
explain only part of underlying returns, with predictability generally
weaker for index options than single-stock options. Practitioner
"max-OI-strike as support/resistance" heuristics are widely used but not
rigorously backtested in anything publicly available.

The credible use, per the research, is as a **confirmation or veto
layer on top of a price-based trigger** (Strategy 1, 3 or 4), not as an
engine on its own. That is how `strategy.py` implements it:
`apply_oi_filter()` takes a directional signal series and only lets it
through when the OI/PCR proxy agrees.

## Specification

Every 3-5 minutes: classify futures price/OI action into long build-up,
short build-up, short covering or long unwinding; track intraday PCR
(put OI / call OI) and its change from the open; watch put/call OI
concentration near spot for support/resistance walls. Confirm a call
entry when futures show long build-up or short covering, PCR is rising
(more put writing below spot), and a price trigger fires (15-minute
high break, or VWAP reclaim). Mirror for puts. Best used to confirm
unwinding of the opposing wall, not fresh writing at it (heavy writing
at a nearby strike is exactly where premium decays fastest).

`strategy.py` includes a synthetic OI/PCR proxy purely so the filter
logic has something to run against in the demo. It is not real option
chain data; wire `apply_oi_filter()` to your broker's live OI feed
before using this for anything real.

## Probability of profit

No credible standalone win rate exists in the evidence, so this is
modelled as an explicit, labelled assumption rather than a measured
result: a base price signal at **45% win rate**, and the same signal at
**50%** when OI/PCR-confirmed (a few points of uplift, which is what the
research suggests a good confirmation filter could plausibly add, not
a proven number). The demo shows the filter passing through about 38%
of raw signals on synthetic data; on real data, the pass rate and the
uplift both need to be measured, not assumed.

## Data requirements

Full option-chain OI snapshots (NSE disseminates OI at intervals, not
tick by tick, so treat it as a slow-moving variable) and futures OI.
Broker WebSocket full-mode quotes include OI; keep chain polling within
your broker's quote rate limits, or subscribe to 20-40 strikes directly
over the WebSocket.

## Failure modes

OI is inherently ambiguous (every contract has a buyer and a seller).
Expiry-day pinning near max-OI strikes is common on Tuesdays. Intraday
OI updates are lagged. Pre-2024 Bank Nifty OI heuristics may not
transfer cleanly now that it is monthly-only.

## Sources

Economies/MDPI 7(1):24, PCR frequency-domain causality study. Singh &
Chaudhary, ICFMCF 2023, Bank Nifty OI/volume study. NiftyTrader PCR and
OI pages (practitioner reference, not a backtest).
