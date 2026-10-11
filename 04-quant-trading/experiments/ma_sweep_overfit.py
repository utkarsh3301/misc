"""
The parameter-sweep trap, on the repo's MACD (moving-average cross) strategy.

The script asks the user for its two windows. A natural thing to do is try many pairs and keep
the best. Here: sweep fast in 3..60 and slow in 10..250 on 2008-2014, keep the best Sharpe, then
look at how that pick, and every other pair, did on 2015-2021.

Execution is honest: signal at close t, held from the open of t+1, 0.1% per side, long only,
equal weight across ~300 CSI300 names.

Usage: python ma_sweep_overfit.py /path/to/qlib_data/cn
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]).expanduser()
cal = pd.to_datetime(pd.read_csv(ROOT / "calendars/day.txt", header=None)[0])


def read(code, f):
    a = np.fromfile(ROOT / "features" / code / f"{f}.day.bin", dtype="<f4")
    return pd.Series(a[1:], index=cal[int(a[0]) : int(a[0]) + len(a) - 1].values)


codes = sorted(p.name for p in (ROOT / "features").iterdir() if p.name.startswith(("sh60", "sz00")))
C = pd.DataFrame({c: read(c, "close") for c in codes}).loc["2007-01-01":"2021-06-01"]
O = pd.DataFrame({c: read(c, "open") for c in codes}).loc[C.index]
oo = (O.shift(-1) / O - 1).values
Cv = C.values
COST = 0.001
IS = (C.index >= "2008-01-01") & (C.index <= "2014-12-31")
OOS = C.index >= "2015-01-01"


def sharpe(d):
    d = d[~np.isnan(d)]
    return d.mean() / d.std() * np.sqrt(252) if d.std() > 0 else np.nan


def run(fast, slow):
    m1 = C.rolling(fast, min_periods=fast).mean().values
    m2 = C.rolling(slow, min_periods=slow).mean().values
    pos = np.where(np.isnan(m2) | np.isnan(Cv), np.nan, (m1 >= m2).astype(float))
    live = np.vstack([np.full((1, pos.shape[1]), np.nan), pos[:-1]])  # signal from t-1 close
    chg = np.abs(np.diff(np.nan_to_num(live), axis=0, prepend=0))
    pnl = live * oo - chg * COST
    return np.nanmean(pnl, axis=1)


res = []
for fast in range(3, 61, 3):
    for slow in range(10, 251, 10):
        if slow <= fast * 1.5:
            continue
        d = run(fast, slow)
        res.append((fast, slow, sharpe(d[IS]), sharpe(d[OOS])))
r = pd.DataFrame(res, columns=["fast", "slow", "sharpe_2008_2014", "sharpe_2015_2021"])
bh = np.nanmean(np.vstack([np.full((1, Cv.shape[1]), np.nan), (Cv[1:] / Cv[:-1] - 1)]), axis=1)

best = r.loc[r.sharpe_2008_2014.idxmax()]
rank_oos = (r.sharpe_2015_2021 > best.sharpe_2015_2021).mean()
print(f"Pairs tested: {len(r)}")
print(f"Best in-sample pair: fast {int(best.fast)}, slow {int(best.slow)}")
print(f"  Sharpe 2008-2014: {best.sharpe_2008_2014:+.2f}   Sharpe 2015-2021: {best.sharpe_2015_2021:+.2f}")
print(f"  {rank_oos:.0%} of all pairs did better than the chosen one in 2015-2021")
print(f"Median pair: Sharpe 2008-2014 {r.sharpe_2008_2014.median():+.2f}, 2015-2021 {r.sharpe_2015_2021.median():+.2f}")
print(f"Buy and hold: Sharpe 2008-2014 {sharpe(bh[IS]):+.2f}, 2015-2021 {sharpe(bh[OOS]):+.2f}")
print(f"Rank correlation of in-sample vs out-of-sample Sharpe across pairs: "
      f"{r.sharpe_2008_2014.rank().corr(r.sharpe_2015_2021.rank()):+.2f}")
top10 = r.nlargest(int(len(r) * 0.1), "sharpe_2008_2014")
print(f"Top 10% in-sample pairs: mean Sharpe {top10.sharpe_2008_2014.mean():+.2f} -> {top10.sharpe_2015_2021.mean():+.2f} out of sample")
