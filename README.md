# NSE options scalping strategies

Seven intraday, option-buying (long call/put) strategies for Nifty, Bank
Nifty and liquid F&O stocks, each researched, specified, and backtested
as far as available data allows.

## Layout

```
strategies/
  common/                 shared cost model, indicators, Monte Carlo POP engine
  01_ema_crossover_scalper/   the original 9/21 EMA idea, refined
  02_vwap_trend_reversion/
  03_orb_premium_breakout/
  04_supertrend_adx_trend/
  05_oi_pcr_filter/
  06_intraday_momentum/
  07_vol_squeeze_breakout/
results/
  run_all.py              regenerates summary.md from all seven strategies
  summary.md              generated comparison table
  METHODOLOGY.md           what the POP numbers are and are not
```

Each strategy folder has a `README.md` (theory, rules, evidence,
probability of profit, failure modes) and a `strategy.py` (signal logic
plus a runnable demo and Monte Carlo simulation).

## Run it

```
pip install numpy pandas
python results/run_all.py
```

This runs a synthetic-data sanity check on each strategy's signal code
and a cost-aware Monte Carlo simulation of probability of profit, then
rewrites `results/summary.md`.

## The headline finding

The original strategy (9/21 EMA cross, 15-second chart, fixed 4-point
target) is not viable as specified. After 2026 NSE costs and realistic
slippage, a fixed 4-point target with a 2.5-point stop needs about a 62%
win rate to break even on 3 lots. Published fast EMA-cross win rates run
25-45%. The refined version in `01_ema_crossover_scalper/` (slower bars,
trend/ADX/volatility filters, cost-scaled target) is a better starting
point, but is still expectancy-negative at the literature's win rate
estimate. See its README for the full case.

Opening range breakout on the option premium (`03_orb_premium_breakout/`)
is the strategy with the strongest India-specific evidence: a real,
post-cost Zerodha backtest at roughly 48% win rate, though with a
drawdown near 45%.

## What this is not

Nothing here is investment advice, and nothing here has been tested
against real historical NSE tick or options data: no licensed data feed
was reachable from the environment this was built in. The probability
of profit figures come from a cost model applied to win rate and
reward-to-risk assumptions sourced from published research and backtests
(cited in each strategy's README), not from live trading results. Read
`results/METHODOLOGY.md` before trusting any number here with real
capital, and paper trade before deploying any of this live.
