# 09. PyPortfolioOpt (portfolio optimisation)

Repo: https://github.com/robertmartin8/PyPortfolioOpt
Studied: shallow clone of `master` and the PyPI package 1.6.0, October 2026.

## What it is

The most widely used open-source Python library for building portfolios: mean-variance
optimisation (max Sharpe, min volatility, efficient frontier), covariance shrinkage,
Black-Litterman, hierarchical risk parity (HRP) and discrete allocation. If you manage money in
Python, there is a good chance a PyPortfolioOpt call sits between your signals and your orders.

## How it works (from the source)

| Piece | File | Detail |
|---|---|---|
| Expected returns | `pypfopt/expected_returns.py` | `mean_historical_return` defaults to the compounded annual growth rate of each stock over the window you pass in. |
| Risk | `pypfopt/risk_models.py` | `sample_cov` (the README default) or shrinkage estimators such as Ledoit-Wolf. |
| Optimiser | `pypfopt/efficient_frontier/efficient_frontier.py` | `max_sharpe()` solves for the tangency portfolio with cvxpy; long only by default. |
| HRP | `pypfopt/hierarchical_portfolio.py` | Clusters stocks by correlation and splits risk down the tree; uses no expected returns. |

The README is honest: it warns that historical mean returns have "a high estimation error, which
is particularly dangerous in mean-variance optimization". Its quick-start still prints
`Expected annual return: 29.9%, Sharpe Ratio: 1.38` for a max-Sharpe portfolio, computed on the
same prices it was fitted to.

## Where the edge is supposed to come from

Combining assets with the best return-to-risk trade-off, instead of holding them equally.

## What I found

**1. The optimiser's promise and the result are an order of magnitude apart.** Every month from
January 2009 to May 2021 I took the 40 most-traded CSI300 members at that date (point in time),
fitted each method on the previous 252 days only, held for one month and charged 0.1% per unit
of turnover:

| Portfolio | Annual return | Volatility | Sharpe | Max drawdown | Monthly turnover | Average largest weight |
|---|---|---|---|---|---|---|
| Equal weight (1/N) | 13% | 28% | 0.45 | -54% | 27% | 2.5% |
| Max Sharpe, sample covariance (README default) | 9% | 37% | 0.25 | -77% | 91% | 44% |
| Max Sharpe, Ledoit-Wolf covariance | 9% | 37% | 0.24 | -77% | 90% | 43% |
| Min volatility, Ledoit-Wolf | 14% | 21% | 0.63 | -40% | 55% | 32% |
| HRP | 14% | 26% | 0.54 | -47% | 48% | 7% |

At each rebalance the max-Sharpe optimiser expected a Sharpe ratio of 4.1 on average. It
delivered 0.25, about half of equal weight, with a deeper drawdown, nearly full turnover every
month and 44% of the money typically in one stock.

**2. The problem is the return estimate, not the covariance.** Shrinking the covariance changed
nothing for max Sharpe (0.25 vs 0.24). Last year's winners are a poor guide to next month, and
max Sharpe bets heavily on them. The two methods that ignore expected returns, min volatility and
HRP, both beat equal weight on risk-adjusted terms. This matches the academic finding that 1/N is
very hard to beat once estimation error is counted (DeMiguel, Garlappi and Uppal, 2009), and the
common observation that minimum-variance portfolios hold up better than mean-variance ones.

**3. HRP crashes on current SciPy.** `HRPOpt.optimize()` checks
`scipy.cluster.hierarchy._LINKAGE_METHODS`, a private attribute that newer SciPy (1.18 here) no
longer has, so it raises `AttributeError`. The experiment script restores the attribute before
calling it. Pin SciPy or patch it the same way.

## The edge, in one line

The library is solid; the edge is in which function you call. Risk-only methods (min volatility,
HRP) added value here. Max Sharpe on historical returns destroyed it, while promising a Sharpe of 4.

## Takeaways for our own work

- Never feed raw historical mean returns into max Sharpe. Use risk-only methods, or expected
  returns from an actual tested signal, and shrink them hard.
- Always print the optimiser's expected Sharpe next to the realised one. The ratio is a direct
  measure of how much you are fooling yourself.
- Cap single-name weights and turnover explicitly; the unconstrained optimum is a concentrated,
  high-churn bet.
- Test the dependency stack, not just the code: a SciPy upgrade quietly disabled HRP.

## Reproduce

```
curl -L -o cn.zip https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_simple_cn_1d_latest.zip
unzip cn.zip -d cn
pip install pyportfolioopt
python experiments/optimiser_out_of_sample.py ./cn
```
