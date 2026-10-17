# EMA crossovers and candlestick price action, backtested on real data

Research branch: can EMA crossover strategies make money on past market
data, can candlestick price action be automated, and how often do they
succeed? Tested on NIFTY 50, BANK NIFTY and 62 NSE stocks (daily
2005-2026, 1-minute 2011-2023) plus seven global markets (2005-2020),
with real costs, next-bar execution and significance tests.

**Read [REPORT.md](REPORT.md) for the findings.** In short:

- Daily, long only EMA crossovers on Indian indices roughly match buy and
  hold returns with half the drawdown (NIFTY 20/50: 7.9% vs 7.5% CAGR,
  -27% vs -60% max drawdown, after 2026 futures costs). Long/short,
  currency and hourly versions do not work.
- Intraday EMA crossovers on NIFTY/BANKNIFTY have a real edge of about
  2 bps per trade before costs and lose money after them in every
  timeframe tested; 2026 costs are about 7 bps per round trip.
- Candlestick patterns are easy to automate (22 implemented) but their
  success rates match base rates; after costs most lose money.

## Layout

```
REPORT.md                 the research report
ema_lab/
  data.py                 loaders and cleaning (sessions, bad days, corporate actions)
  indicators.py           EMA, ATR, ADX, RSI, MACD
  patterns.py             22 rule based candlestick patterns + trend context
  costs.py                NSE 2026 and global cost assumptions
  engine.py               bar by bar backtester (numba): next open fills, stops, targets
  metrics.py              win rate, profit factor, CAGR, Sharpe, drawdown, ...
  strategies.py           EMA family, intraday session rules, pattern trades, hybrids
  stats.py                random entry test, bootstrap, deflated Sharpe threshold
scripts/
  fetch_data.py           download and convert the public datasets
  run_ema_daily.py        daily EMA experiments (indices, stocks, global)
  run_ema_intraday.py     intraday EMA experiments (1m to 30m)
  run_candles.py          candlestick event study, tradable versions, EMA hybrids
  build_scoreboard.py     headline success percentage tables
results/
  ema_daily.md, ema_intraday.md, candles.md, scoreboard.md   generated digests
  tables/                 every result as CSV
  figures/                charts used in the report
tests/test_engine.py      execution rule tests for the engine
```

## Reproduce

```
pip install -r requirements.txt
python scripts/fetch_data.py
python scripts/run_ema_daily.py
python scripts/run_ema_intraday.py
python scripts/run_candles.py
python scripts/build_scoreboard.py
python -m pytest tests
```

`fetch_data.py` uses partial, sparse git clones of three public GitHub
repositories and only downloads the files it needs. Raw and processed
data stay out of git (`data/` is ignored); the results in `results/` are
committed.

Related: the `algo` branch specifies seven NSE options scalping strategies
and estimates their probability of profit by Monte Carlo from published
win rates, because no historical data was available there. Section 6 of
the report tests that branch's original 9/21 one-minute idea on real
data.

Nothing here is investment advice.
