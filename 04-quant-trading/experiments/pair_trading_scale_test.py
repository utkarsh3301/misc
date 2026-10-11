"""
Is the repo's pair-trading strategy invariant to the units prices are quoted in?

A correct pairs strategy must make the same trades if both price series are multiplied
by 10 (think of quoting in paise instead of rupees). In je-suis-tm/quant-trading's
"Pair trading backtest.py" the entry bands are built as
    z_upper = z_now + std(residual)      (std of the residual in PRICE units)
    z_lower = z_now - std(residual)
which adds a price-unit quantity to a unitless z-score. This script runs the repo's own
signal_generation and EG_method functions on real bank-stock pairs, unscaled and x10.

Run with pandas 2.x: the repo relies on chained assignment (signals['z'].iloc[i:] = ...),
which pandas 3 copy-on-write silently ignores, so under pandas 3 the strategy never trades.

Usage: python pair_trading_scale_test.py /path/to/quant-trading /path/to/qlib_data/cn
"""
import importlib.util
import sys
import types
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
REPO, DATA = Path(sys.argv[1]), Path(sys.argv[2])
sys.modules["yfinance"] = types.ModuleType("yfinance")  # repo imports it at top level; not used here
import matplotlib

matplotlib.use("Agg")
spec = importlib.util.spec_from_file_location("pairs", REPO / "Pair trading backtest.py")
pairs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pairs)

cal = pd.to_datetime(pd.read_csv(DATA / "calendars/day.txt", header=None)[0])


def close(code):
    a = np.fromfile(DATA / "features" / code / "close.day.bin", dtype="<f4")
    s = pd.Series(a[1:], index=cal[int(a[0]) : int(a[0]) + len(a) - 1].values)
    return s


# bank and insurer pairs, the classic textbook candidates
PAIRS = [("sh600036", "sh601166"), ("sh601398", "sh601939"), ("sh600000", "sh600016"), ("sh601318", "sh601601")]
print(f"{'pair':22s} {'scale':>5s} {'entries':>8s}")
for a, b in PAIRS:
    df = pd.concat([close(a), close(b)], axis=1, keys=[a, b]).loc["2013-01-01":"2014-12-31"].dropna()
    for scale in (1, 10):
        s1 = pd.DataFrame({"Close": df[a] * scale})
        s2 = pd.DataFrame({"Close": df[b] * scale})
        sig = pairs.signal_generation(s1, s2, pairs.EG_method)
        entries = int((sig["positions1"].fillna(0) != 0).sum())
        print(f"{a}/{b:13s} {scale:5d} {entries:8d}")
print("\nIf the strategy were correct, the 'entries' count would be identical for scale 1 and 10.")
