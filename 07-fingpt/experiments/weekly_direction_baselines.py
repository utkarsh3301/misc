"""
What does a weekly up/down "forecaster" have to beat?

FinGPT-Forecaster turns each stock-week into a label like U3 (up 2-3%) or D5+ (down more than 5%)
via bin_mapping() in fingpt/FinGPT_Forecaster/data.py, using weekly ('W') resampled closes,
and was released after fine-tuning on DOW30 data from 2022-12-30 to 2023-09-01.

This script measures the zero-intelligence baselines on CSI300 stocks, year by year:
  always_up     predict "up" for every stock every week
  market_dir    predict every stock moves the way the index moved that week
                (an upper bound on how much of "accuracy" is just the market)
  last_week     predict the same direction as the stock's previous week
plus the sampling error of an accuracy measured on ~1,000 stock-weeks (30 stocks x 35 weeks).

Usage: python weekly_direction_baselines.py /path/to/qlib_data/cn
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]).expanduser()
cal = pd.to_datetime(pd.read_csv(ROOT / "calendars/day.txt", header=None)[0])


def read_close(code):
    a = np.fromfile(ROOT / "features" / code / "close.day.bin", dtype="<f4")
    return pd.Series(a[1:], index=cal[int(a[0]) : int(a[0]) + len(a) - 1].values)


codes = sorted(p.name for p in (ROOT / "features").iterdir() if p.name.startswith(("sh60", "sz00")))
C = pd.DataFrame({c: read_close(c) for c in codes})
W = C.resample("W").last()  # same weekly sampling as the Forecaster
R = W.pct_change(fill_method=None).iloc[1:]
idx = read_close("sh000300").resample("W").last().pct_change().reindex(R.index)

up = R > 0
valid = R.notna() & (R != 0)
rows = []
for y, g in R.groupby(R.index.year):
    v = valid.loc[g.index]
    u = up.loc[g.index]
    always_up = u[v].stack().mean()
    mkt = (u.eq(idx.loc[g.index] > 0, axis=0))[v].stack().mean()
    last = (u == up.shift(1).loc[g.index])[v & valid.shift(1, fill_value=False).loc[g.index]].stack().mean()
    rows.append((y, always_up, mkt, last, int(v.values.sum())))
t = pd.DataFrame(rows, columns=["year", "always_up", "market_dir", "last_week", "stock_weeks"]).set_index("year")
print(t.to_string(float_format=lambda x: f"{x:.1%}"))
n = 30 * 35
print(f"\nStandard error of an accuracy near 55% measured on {n} stock-weeks: +/-{np.sqrt(.55*.45/n):.1%}"
      " (and stock-weeks in the same week are highly correlated, so the true error is larger)")
herd = (up[valid].mean(axis=1) - 0.5).abs() > 0.2
print(f"Weeks where more than 70% of stocks moved the same way: {herd.mean():.0%}")
