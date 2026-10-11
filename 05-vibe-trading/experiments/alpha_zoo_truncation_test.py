"""
Independent look-ahead check of Vibe-Trading's Alpha Zoo (Alpha 101, GTJA 191, Qlib 158, academic).

Same truncation idea as 08-ta-libraries: a factor value for day t must not change when every
bar after t is deleted. Each alpha is computed through the project's own Registry.compute() on a
panel of 40 CSI300 stocks (2016-2020), then recomputed on the panel cut at several dates.

vwap is approximated as (high + low + close) / 3 and amount as vwap * volume. Alphas needing sector,
market cap or fundamentals are skipped by the registry itself.

Usage: python alpha_zoo_truncation_test.py /path/to/Vibe-Trading /path/to/qlib_data/cn
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
VT, DATA = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(VT / "agent"))
from src.factors.registry import Registry, SkipAlpha  # noqa: E402

cal = pd.to_datetime(pd.read_csv(DATA / "calendars/day.txt", header=None)[0])


def read(code, f):
    a = np.fromfile(DATA / "features" / code / f"{f}.day.bin", dtype="<f4")
    return pd.Series(a[1:], index=cal[int(a[0]) : int(a[0]) + len(a) - 1].values).astype("float64")


codes = sorted(p.name for p in (DATA / "features").iterdir() if p.name.startswith(("sh60", "sz00")))
F = {f: pd.DataFrame({c: read(c, f) for c in codes}).loc["2016-01-01":"2020-12-31"]
     for f in ["open", "high", "low", "close", "volume"]}
keep = F["close"].notna().mean().sort_values(ascending=False).index[:40]
panel = {f: v[keep].ffill() for f, v in F.items()}
panel["vwap"] = (panel["high"] + panel["low"] + panel["close"]) / 3
panel["amount"] = panel["vwap"] * panel["volume"]
panel["returns"] = panel["close"].pct_change()
n = len(panel["close"])
rng = np.random.default_rng(3)
cuts = sorted(rng.choice(np.arange(300, n - 20), size=6, replace=False))

reg = Registry()
ids = reg.list()
tested, skipped, errors, leaky = 0, 0, 0, []
for aid in ids:
    try:
        full = reg.compute(aid, panel)
    except SkipAlpha:
        skipped += 1
        continue
    except Exception:
        errors += 1
        continue
    tested += 1
    bad = 0
    for k in cuts:
        part = reg.compute(aid, {c: v.iloc[: k + 1] for c, v in panel.items()})
        a, b = full.iloc[k], part.iloc[-1]
        both = a.notna() | b.notna()
        diff = ~np.isclose(a[both].fillna(np.inf), b[both].fillna(np.inf), rtol=1e-6, atol=1e-9)
        bad += int(diff.any())
    if bad:
        leaky.append((aid, bad))
print(f"Alphas tested: {tested}, skipped by registry (missing extras): {skipped}, errors: {errors}")
print(f"Alphas whose value on day t changed when later bars were removed: {len(leaky)}")
for aid, b in leaky:
    print(f"  {aid}: {b}/{len(cuts)} cut dates")
