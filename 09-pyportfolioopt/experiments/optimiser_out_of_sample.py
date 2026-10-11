"""
Does mean-variance optimisation with PyPortfolioOpt beat equal weight out of sample?

The README's quick-start prints "Expected annual return: 29.9%, Sharpe Ratio: 1.38" for a
max-Sharpe portfolio, estimated and evaluated on the same price history. Here every month we:
  1. take current CSI300 members (point in time) with a full year of history,
  2. keep the 40 most traded over the last 60 days,
  3. build portfolios from the past 252 days only,
  4. hold them for the next month, paying 0.1% per unit of turnover.

Portfolios:
  equal_weight         1/N
  max_sharpe_sample    README quick-start: mean_historical_return + sample_cov + max_sharpe
  max_sharpe_shrunk    same, Ledoit-Wolf covariance
  min_volatility       Ledoit-Wolf covariance, min_volatility
  hrp                  HRPOpt (hierarchical risk parity)

Usage: python optimiser_out_of_sample.py /path/to/qlib_data/cn
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from pypfopt import EfficientFrontier, HRPOpt, expected_returns, risk_models

# PyPortfolioOpt 1.6.0 checks a private SciPy attribute that newer SciPy removed, so HRPOpt
# raises AttributeError. Restore it so HRP can be tested.
if not hasattr(sch, "_LINKAGE_METHODS"):
    sch._LINKAGE_METHODS = {"single", "complete", "average", "weighted", "centroid", "median", "ward"}

warnings.filterwarnings("ignore")
ROOT = Path(sys.argv[1]).expanduser()
cal = pd.to_datetime(pd.read_csv(ROOT / "calendars/day.txt", header=None)[0])
spans = pd.read_csv(ROOT / "instruments/csi300.txt", sep="\t", header=None, names=["code", "start", "end"])
spans[["start", "end"]] = spans[["start", "end"]].apply(pd.to_datetime)


def read(code, f):
    p = ROOT / "features" / code.lower() / f"{f}.day.bin"
    a = np.fromfile(p, dtype="<f4")
    return pd.Series(a[1:], index=cal[int(a[0]) : int(a[0]) + len(a) - 1].values).astype("float64")


codes = [c for c in spans.code.unique() if (ROOT / "features" / c.lower()).exists()]
C = pd.DataFrame({c: read(c, "close") for c in codes}).loc["2007-01-01":"2021-05-31"]
V = pd.DataFrame({c: read(c, "volume") for c in codes}).loc[C.index]
R = C.pct_change(fill_method=None)
month_ends = C.groupby([C.index.year, C.index.month]).tail(1).index
month_ends = month_ends[month_ends >= "2009-01-01"]


def members(d):
    m = spans[(spans.start <= d) & (spans.end >= d)].code
    return [c for c in m if c in C.columns]


def build(prices):
    out, info = {}, {}
    n = prices.shape[1]
    out["equal_weight"] = pd.Series(1 / n, index=prices.columns)
    mu = expected_returns.mean_historical_return(prices)
    S_sample = risk_models.sample_cov(prices)
    S_lw = risk_models.CovarianceShrinkage(prices).ledoit_wolf()
    for name, S in [("max_sharpe_sample", S_sample), ("max_sharpe_shrunk", S_lw)]:
        try:
            ef = EfficientFrontier(mu, S)
            ef.max_sharpe()
            w = pd.Series(ef.clean_weights())
            info[name] = ef.portfolio_performance()[2]  # the Sharpe the optimiser expects
            out[name] = w
        except Exception:
            out[name] = out["equal_weight"]
    try:
        ef = EfficientFrontier(None, S_lw)
        ef.min_volatility()
        out["min_volatility"] = pd.Series(ef.clean_weights())
    except Exception:
        out["min_volatility"] = out["equal_weight"]
    try:
        out["hrp"] = pd.Series(HRPOpt(prices.pct_change().dropna()).optimize())
    except Exception:
        out["hrp"] = out["equal_weight"]
    return out, info


names = ["equal_weight", "max_sharpe_sample", "max_sharpe_shrunk", "min_volatility", "hrp"]
daily = {k: [] for k in names}
prev = {k: pd.Series(dtype=float) for k in names}
turn = {k: [] for k in names}
maxw = {k: [] for k in names}
promised = []
for i, d in enumerate(month_ends[:-1]):
    nxt = month_ends[i + 1]
    pos = C.index.get_loc(d)
    hist = C.iloc[pos - 251 : pos + 1]
    cand = [c for c in members(d) if hist[c].notna().mean() >= 0.95]  # allow a few missing days
    liq = (C[cand].iloc[pos - 59 : pos + 1] * V[cand].iloc[pos - 59 : pos + 1]).mean().sort_values(ascending=False)
    pick = list(liq.index[:40])
    ws, info = build(hist[pick].ffill().bfill())
    if "max_sharpe_sample" in info:
        promised.append(info["max_sharpe_sample"])
    fwd = R.loc[(R.index > d) & (R.index <= nxt), pick].fillna(0)
    for k in names:
        w = ws[k].reindex(pick).fillna(0)
        w = w / w.sum()
        to = w.subtract(prev[k], fill_value=0).abs().sum()
        r = fwd.values @ w.values
        r[0] -= to * 0.001
        daily[k].append(pd.Series(r, index=fwd.index))
        turn[k].append(to)
        maxw[k].append(w.max())
        prev[k] = w

rows = []
for k in names:
    s = pd.concat(daily[k])
    eq = (1 + s).cumprod()
    rows.append((k, s.mean() * 252, s.std() * np.sqrt(252), s.mean() / s.std() * np.sqrt(252),
                 (eq / eq.cummax() - 1).min(), np.mean(turn[k][1:]), np.mean(maxw[k])))
t = pd.DataFrame(rows, columns=["portfolio", "ann_return", "ann_vol", "sharpe", "max_drawdown",
                                "monthly_turnover", "avg_max_weight"]).set_index("portfolio")
print(f"Monthly rebalance, 40 most-traded CSI300 members, {month_ends[0].date()} to {month_ends[-1].date()}, 0.1% cost per unit turnover\n")
print(t.to_string(float_format=lambda x: f"{x:.2f}"))
print(f"\nSharpe the max-Sharpe (sample cov) optimiser expected at each rebalance, average: {np.mean(promised):.2f}")
