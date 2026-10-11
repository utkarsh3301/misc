# 10. backtrader (event-driven backtesting engine)

Repo: https://github.com/mementum/backtrader
Studied: shallow clone of `master` (last commit April 2023) and the PyPI package 1.9.78.123.

## What it is

One of the most used Python backtesting engines, especially among retail and semi-professional
traders. You write a `Strategy` class, add data feeds, brokers and analyzers to a `Cerebro`,
and it simulates the orders bar by bar. It is no longer
actively maintained: the last commit is from April 2023.

## How it works (from the source)

| Piece | File | Default |
|---|---|---|
| Order timing | `brokers/bbroker.py` | A market order created in `next()` on bar t fills at the open of bar t+1. `coc` (cheat-on-close) and `coo` (cheat-on-open) are off. |
| Costs | `comminfo.py`, `brokers/bbroker.py` | `commission = 0.0`, `slip_perc = 0.0`, `slip_fixed = 0.0`. Zero cost unless you set it. |
| Sharpe analyzer | `analyzers/sharpe.py` | `timeframe = Years`, `riskfreerate = 0.01`, `stddev_sample = False`. |

## Where the edge is supposed to come from

None, it is an engine. The question here is whether its defaults flatter the strategies run on it.

## What I found

**1. Order timing is honest by default.** In 100% of my runs a market order placed on bar t
filled exactly at bar t+1's open. Compare with the same-close fills in 04-quant-trading: this is
the right default.

**2. Costs are zero by default.** A strategy run without `broker.setcommission(...)` and a
slippage setting trades for free. For Indian delivery equity that silently drops about 0.22% per
round trip (see the NSE notes in the top-level README).

**3. The default Sharpe ratio is built from one number per year.** Unless you pass a
`timeframe`, `SharpeRatio` resamples the equity curve to calendar years and takes the mean and
population standard deviation of those yearly returns. On a 3-year backtest that is a Sharpe
from 3 data points. I ran the same buy-and-hold strategy through backtrader on CSI300 stocks and
read both the default analyzer and one set to daily returns (`timeframe=Days, annualize=True`):

| Window | Stocks | Median gap between the two Sharpes | Largest gap | Rank correlation |
|---|---|---|---|---|
| 3 years (2017-2019) | 57 | 0.16 | 2.54 | 0.96 |
| 9 years (2011-2019) | 54 | 0.04 | 0.31 | 0.99 |

Most of the time the two agree, but when yearly returns happen to be similar the default
explodes: one stock lost steadily and scored -2.87 on the default analyzer against -0.33 from
daily data. The same arithmetic produces a spectacular positive Sharpe for a strategy that
happened to make a similar amount in each of three years.

## The edge, in one line

A sound engine with honest order timing; the risks are its zero-cost defaults and a yearly
Sharpe analyzer that is easy to misread on short backtests. It is also unmaintained, so new
library versions can break it without anyone fixing it.

## Takeaways for our own work

- Always set commission and slippage explicitly; treat a run without them as unfinished.
- Compute Sharpe from daily returns (`timeframe=bt.TimeFrame.Days, annualize=True`), or take the
  returns out with the `TimeReturn` analyzer and compute it yourself.
- Report the number of independent periods behind any ratio. "Sharpe 2.5 from 3 points" is not a
  result.

## Reproduce

```
curl -L -o cn.zip https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_simple_cn_1d_latest.zip
unzip cn.zip -d cn
pip install backtrader
python experiments/sharpe_analyzer_check.py ./cn
```
