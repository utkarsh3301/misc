# Strategy 1: Dual EMA (9/21) crossover scalper

## The original idea

9-period EMA and 21-period EMA on a 15-second candle chart, evaluated
continuously. On a bullish cross (9 EMA above 21 EMA), buy a call. On a
bearish cross, buy a put. Orders placed roughly every 1-2 minutes, not
on every 15-second bar. Exit once "4 points" of profit are collected.

## Why it needs rework, not tuning

**15-second resolution is not really viable for the signal.** Zerodha's
Kite Connect WebSocket gives "a maximum of 1 tick per second per
instrument", occasionally 2 for Nifty 50, with average latency of
500-700ms measured by users on the Kite forum. A 15-second bar is built
from at most about 15 already-stale samples. After order round-trip
time, a realistic signal-to-fill delay is 1-2 seconds, which is 7-13% of
the bar itself.

**A fixed 4-point target is economically thin.** On 1 lot of Nifty
(lot size 65 from December 2025), a round trip from 100 to 104 premium
costs about 0.97 points in brokerage, STT, exchange charges, stamp duty
and GST alone (see `strategies/common/costs.py`, validated against the
research report's worked example). Add slippage and a symmetric 4/4
target/stop needs roughly a 67-75% win rate to break even. Published
win rates for fast moving-average cross systems run 25-35% (Zarattini &
Aziz, SSRN 4631351, 9-period MA flip on 1-minute QQQ bars: 30% hit
ratio, 107,067 trades, 41% max drawdown).

**Whipsaw is the real enemy.** An independent Indian backtest
(github.com/anirudhatalmale6-alt/nifty-banknifty-intraday-trend-algo)
of a similar trend-following system found gross profit factor of 1.55
falling to 1.27 after statutory charges, 1.01 at 2 bps slippage, and
0.82 at 4 bps: "friction took essentially the entire edge." Its
conclusion: filters that cut trade count are worth more than filters
that raise the win rate.

## Refined specification (implemented in `strategy.py`)

- **Signal timeframe:** 1-minute bars (15-second data used only for
  entry timing, not the crossover signal itself).
- **Entry:** 9/21 EMA cross confirmed for at least 2 consecutive
  1-minute bars (not the instant of the raw cross), with spread beyond
  0.15x ATR(14), EMA21 slope agreeing with direction, price on the
  correct side of session VWAP, and 5-minute ADX above 20.
- **Time windows:** 09:20-11:30 and 13:30-14:45. Flat by 15:10.
- **Exit:** target and stop should scale with cost (research recommends
  `target = max(4, k x round-trip cost, m x ATR of premium)`); this
  reference implementation uses a fixed 4-point target / 2.5-point stop
  as a starting point, plus a 5-bar time stop.
- **Sizing:** 3 lots of Nifty, so the fixed cost per lot is spread
  thinner (a 1-lot target keeps only ~2 points net of an already-thin
  4-point move; more lots make the fixed brokerage/GST component matter
  less per point).

Implementation note: the higher-timeframe filter here uses session VWAP
only, as a simplification. The research also recommends a 15-minute
EMA21 slope confirmation on top of this; add it before trusting this
against real capital.

## Data and infrastructure

Index/futures 1-minute (or better) OHLCV for the signal, a live option
chain for the 2-4 candidate strikes, and your own tick recorder if you
want to backtest sub-minute bars (broker historical APIs cap out at
1-minute granularity). Order frequency here (roughly 1 per 1-2 minutes)
is trivial against SEBI's 10-orders-per-second retail algo threshold.

## Probability of profit

- Literature range for the refined, filtered version: **40-55% win
  rate** (my synthesis, not a measured result); unfiltered fast crosses
  measure 25-35% in the cited studies.
- Monte Carlo result at the 47.5% midpoint, 4-point target, 2.5-point
  stop, 3 lots: **breakeven win rate is about 62%, so POP over 250
  trades comes out near 0%** (see `results/summary.md`). This is the
  single most important number in this repo: the refined version, as
  currently parameterized, is not yet expectancy-positive at the
  literature's win rate. Either the real win rate needs to be
  meaningfully above 55%, or the target/stop/lot sizing needs to widen
  the reward-to-risk further before this is worth trading. Run
  `strategies/common/monte_carlo.run_sensitivity()` to see exactly what
  win rate would flip this to net-positive.

## Option-buying considerations

Use 0.5-0.65 delta strikes (ATM to slightly ITM) so index moves actually
translate into premium moves; avoid cheap far-OTM "lottery" strikes.
Avoid the last 60-90 minutes of Tuesday (weekly) expiry, when gamma
dominates the EMA signal.

## Failure modes

Lunchtime chop, narrow-range days, gap opens the EMAs lag into, and
event days (RBI policy, Budget, CPI, Fed). NSE's algo share of equity
derivatives turnover hit about 70% in FY25 per NSE's Market Pulse
report; fast, public, simple signals like this compete directly with
faster participants.

## Compliance (applies to all seven strategies)

SEBI's retail algo framework (circular 4 Feb 2025, fully applicable
since 1 April 2026) requires broker-routed APIs only, a static
whitelisted IP, 2FA, and exchange-assigned Algo-ID tagging on every
order. A self-built personal algo under 10 orders per second per
exchange does not need individual strategy registration; all seven
strategies in this repo run at well under 1 order per second. Confirm
specifics with your broker's compliance desk before going live,
especially if you ever run this for anyone other than yourself.

## Sources

Zarattini & Aziz, SSRN 4631351. Kite Connect docs and forum
(kite.trade/docs, kite.trade/forum). Zerodha Z-Connect on the retail
algo circular. github.com/anirudhatalmale6-alt/nifty-banknifty-intraday-trend-algo.
NSE Market Pulse via Business Standard, 23 Jul 2025. Angel One on the
Dec 2025 lot size revision. Full source list in the research report
this repo was built from.
