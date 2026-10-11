"""
How much of an "accept the factor if the backtest improves" loop is real, and how much is
selection on the test period?

RD-Agent(Q)'s factor loop (rdagent/scenarios/qlib/developer/feedback.py) shows the LLM the
TEST-segment IC and excess annualised return (backtest starts at test_start, 2017-01-01 by
default) of the new factor set vs the current best, and its prompt says
"Any small improvement should be considered for inclusion as SOTA".

Here a dumb proposer replaces the LLM: it draws random price/volume formulas, and the same
greedy rule keeps a formula whenever the combined signal's 2017-01..2020-07 rank IC improves.
We then score the final library on periods the loop never looked at.
A second run uses pure-noise "factors" to show what selection alone produces.

Usage: python greedy_test_set_selection.py /path/to/qlib_data/cn
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]).expanduser()
cal = pd.to_datetime(pd.read_csv(ROOT / "calendars/day.txt", header=None)[0])
spans = pd.read_csv(ROOT / "instruments/csi300.txt", sep="\t", header=None, names=["code", "start", "end"])
spans[["start", "end"]] = spans[["start", "end"]].apply(pd.to_datetime)


def read(code, f):
    p = ROOT / "features" / code.lower() / f"{f}.day.bin"
    a = np.fromfile(p, dtype="<f4")
    return pd.Series(a[1:], index=cal[int(a[0]) : int(a[0]) + len(a) - 1].values)


codes = [c for c in spans.code.unique() if (ROOT / "features" / c.lower()).exists()]
C = pd.DataFrame({c: read(c, "close") for c in codes}).loc["2014-01-01":"2021-06-01"]
V = pd.DataFrame({c: read(c, "volume") for c in codes}).loc[C.index]
H = pd.DataFrame({c: read(c, "high") for c in codes}).loc[C.index]
L = pd.DataFrame({c: read(c, "low") for c in codes}).loc[C.index]
member = pd.DataFrame(False, index=C.index, columns=C.columns)
for _, r in spans.iterrows():
    if r.code in member:
        member.loc[(member.index >= r.start) & (member.index <= r.end), r.code] = True
label = C.shift(-2) / C.shift(-1) - 1

rng = np.random.default_rng(0)
OPS = ["roc", "ma", "std", "max", "min", "vma", "corr", "rsv"]


def formula(op, w):
    if op == "roc": return C.shift(w) / C
    if op == "ma": return C.rolling(w).mean() / C
    if op == "std": return C.rolling(w).std() / C
    if op == "max": return H.rolling(w).max() / C
    if op == "min": return L.rolling(w).min() / C
    if op == "vma": return V.rolling(w).mean() / (V + 1e-12)
    if op == "corr": return C.rolling(w).corr(np.log(V + 1))
    if op == "rsv": return (C - L.rolling(w).min()) / (H.rolling(w).max() - L.rolling(w).min() + 1e-12)


idx = member.stack()
idx = idx[idx].index
y = label.stack().reindex(idx)
keep = y.notna()
idx, y = idx[keep], y[keep]
dates = idx.get_level_values(0)
yrank = y.groupby(level=0).rank(pct=True)


def zs(f):
    s = f.replace([np.inf, -np.inf], np.nan).stack().reindex(idx)
    g = s.groupby(level=0)
    return ((s - g.transform("mean")) / (g.transform("std") + 1e-12)).fillna(0).values.astype("float32")


SEG = {
    "selection 2017-01..2020-07 (seen by loop)": (dates >= "2017-01-01") & (dates <= "2020-07-31"),
    "2015-2016 (never seen)": (dates >= "2015-01-01") & (dates <= "2016-12-31"),
    "2020-08..2021-05 (never seen)": (dates >= "2020-08-01"),
}
SEL = list(SEG)[0]


def rank_ic(score, mask):
    s = pd.Series(score[mask], index=idx[mask])
    r = s.groupby(level=0).rank(pct=True)
    yr = yrank[mask]
    df = pd.DataFrame({"r": r.values, "y": yr.values}, index=dates[mask])
    return df.groupby(level=0).apply(lambda g: g["r"].corr(g["y"])).mean()


def greedy(pool, iters=80, name=""):
    lib, combo, best = [], np.zeros(len(idx), dtype="float32"), -1.0
    for _ in range(iters):
        k = rng.integers(len(pool))
        cand = (combo * len(lib) + pool[k]) / (len(lib) + 1)
        ic = rank_ic(cand, SEG[SEL])
        if ic > best:  # "any small improvement"
            lib.append(k); combo, best = cand, ic
    print(f"\n{name}: kept {len(lib)} of {iters} proposals")
    for seg, m in SEG.items():
        print(f"  rank IC {seg:42s} {rank_ic(combo, m):+.4f}")


print("Building random formula pool...")
pool = []
for _ in range(60):
    op, w, sign = OPS[rng.integers(len(OPS))], int(rng.integers(3, 61)), rng.choice([-1, 1])
    pool.append(sign * zs(formula(op, w)))
greedy(pool, name="Random price/volume formulas, greedy on the selection window")

noise = [rng.standard_normal(len(idx)).astype("float32") for _ in range(60)]
greedy(noise, name="Pure noise factors, same greedy rule")
