# Methodology, and its limits

## Why this is not a historical backtest

Building a real backtest needs historical tick or 1-second option
premium data for Nifty and Bank Nifty. That data is not free or openly
reachable: NSE does not publish it, and the environment this repo was
built in only has outbound network access to package registries and
GitHub (confirmed by a failed Yahoo Finance request during development,
`ConnectionError` on a proxy that blocks general internet hosts). Buying
vendor tick data, or recording your own feed from a broker API over
weeks or months, is the actual next step if you want a real backtest.

So instead of pretending to have historical evidence this repo does not
have, it does two honest things:

1. **A real, correct cost model** (`strategies/common/costs.py`) for NSE
   options in 2026: brokerage, STT, exchange transaction charges, SEBI
   fee, stamp duty, GST, matched against worked examples in the research
   report to 1-2 rupees.
2. **A cost-aware Monte Carlo simulator**
   (`strategies/common/monte_carlo.py`) that takes a win rate and a
   reward-to-risk profile as *inputs*, sourced from published,
   independently-run backtests and academic studies (cited per
   strategy), and asks: given that assumed edge, and the real cost
   model, what is the probability of being net profitable over a run of
   trades, and how bad can the drawdown get.

The "probability of profit" numbers in each README and in
`results/summary.md` are the output of step 2. They are conditional
statements: *if* the win rate is what the cited literature suggests,
*then* this is the probability of profit and this is the expected
drawdown. They are not a claim that the strategy actually has that win
rate on live Nifty options. Only your own paper trading or live
execution data can tell you that.

## Why there is still Python code that runs on synthetic data

Each strategy's `strategy.py` implements the actual signal logic (EMA
crossover detection, VWAP bands, Supertrend, ADX, opening range,
Bollinger/Keltner squeeze) as real, reusable pandas code. `demo()` in
each file runs that logic against synthetic 1-minute OHLCV bars
(`strategies/common/synthetic_data.py`), purely to prove the code runs
end to end and produces a plausible number of signals per day. This is
an integration test, not a performance test. The synthetic generator is
a volatility-shaped random walk with a session regime label (trending
up, trending down, or chop); it has no relationship to actual Nifty
price dynamics beyond a roughly realistic intraday volatility shape.

## Reading the Monte Carlo output

For each strategy, `pop_simulation()` runs several thousand simulated
sequences of N trades (default 250, roughly a trading year at one trade
per day). Each trade's outcome is a coin flip at the assumed win rate,
with win/loss magnitude drawn from a normal distribution around the
assumed average, then run through the real cost model to get a rupee
P&L. Across all simulated sequences it reports:

- `pop`: the fraction of simulated 250-trade sequences that ended net
  positive.
- `expectancy_per_trade_rupees`: average P&L per trade across all
  simulated trades.
- `p05_max_drawdown_rupees`: the 5th percentile worst peak-to-trough
  drawdown across simulated sequences (i.e. a bad-but-plausible case,
  not the absolute worst case).

Run `strategies/common/monte_carlo.run_sensitivity()` with a grid of win
rates to see how fast POP moves if the true win rate is a few points
off the assumption, before risking capital on any of this.

## Before deploying any of this live

- Confirm your own measured slippage on your broker's execution; the
  0.5-point-per-side default here is a placeholder from the research
  report, not something measured on your account.
- Re-run the Monte Carlo with your own fills after a few weeks of paper
  trading, not the literature win rate.
- Check the current SEBI/exchange retail algo rules with your broker
  before running anything as an automated algo (static IP, 2FA,
  Algo-ID tagging; see the EMA strategy README for a summary, and your
  broker's compliance desk for anything binding).
