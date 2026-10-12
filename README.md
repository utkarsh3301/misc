# verify: are there option-trading edges that can actually be verified?

A study of systematic option-trading edges, graded by whether the evidence for them holds up.
Start with [REPORT.md](REPORT.md). Short version:

- No strategy examined meets the bar of a definite, verifiable edge (positive after realistic costs, statistically
  robust to fat tails and multiple testing, persistent out of sample, survivable tail).
- The S&P 500 volatility risk premium is real on average and was detectable in 2014 to 2018 real data, but it is
  crash-risk compensation, about 1.7 vol points of selling concession erases the mean payoff of the variance proxy,
  one bad window erased about 19 months of average gains, and a 5-year record cannot verify it.
- Single-stock option anomalies have the strongest gross statistics in the literature; their status net of costs
  for a non-institutional trader is unresolved.
- Retail 0DTE and weekly buying, long out-of-the-money hedges and "free yield" claims have negative evidence.
- Definite but not alpha: US Section 1256 tax treatment of broad-based index options, European cash-settled SPX.

## Limits to know before relying on it

The sandbox's network policy blocked every market-data host needed (Cboe, FRED, Yahoo, Stooq, Ken French, ...),
so there is no option-chain or index-level backtest here. Real data used is the S&P 500 (1999 to 2018), VIX
(2014 to 2018) and Fama-French monthly factors bundled in the `arch` package. Literature numbers come from
web-search summaries and are second-hand; see `ledger/claims.md` for each claim, its source and a status code.
REPORT.md section 8 lists what to unlock to finish the verification.

## Reproduce

```
pip install -r requirements.txt
bash run_all.sh
```

## Layout

- `REPORT.md` the study. `ledger/claims.md` the source-tracked claims.
- `src/` shared code, including `putwrite.py` (a ready harness for Design A, tested on a hand-built fixture only). `scripts/` one script per analysis. `tests/` unit tests (look-ahead checks included).
- `results/` JSON, CSV and text logs of every analysis; `results/figures/` charts with CSV copies of their data.
