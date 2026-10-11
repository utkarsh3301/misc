"""
Same truncation test for stockstats, the indicator library TradingAgents' market analyst uses
(tradingagents/dataflows/vendors/yahoo/market.py: close_50_sma, close_200_sma, close_10_ema,
macd, macds, macdh, rsi, boll, boll_ub, boll_lb, atr, vwma, mfi), plus other common stockstats
indicators.

Usage: python stockstats_check.py /path/to/qlib_data/cn
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from stockstats import wrap

warnings.filterwarnings("ignore")
ROOT = Path(sys.argv[1]).expanduser()
cal = pd.to_datetime(pd.read_csv(ROOT / "calendars/day.txt", header=None)[0])


def read(f):
    a = np.fromfile(ROOT / "features" / "sh600000" / f"{f}.day.bin", dtype="<f4")
    return pd.Series(a[1:], index=cal[int(a[0]) : int(a[0]) + len(a) - 1].values).astype("float64")


df = pd.DataFrame({f: read(f) for f in ["open", "high", "low", "close", "volume"]}).loc["2012":"2020"].dropna()
df.index.name = "date"
rng = np.random.default_rng(1)
cuts = sorted(rng.choice(np.arange(300, len(df) - 40), size=40, replace=False))

USED_BY_TRADINGAGENTS = ["close_50_sma", "close_200_sma", "close_10_ema", "macd", "macds", "macdh", "rsi",
                         "boll", "boll_ub", "boll_lb", "atr", "vwma", "mfi"]
OTHERS = ["kdjk", "kdjd", "kdjj", "cr", "wr", "cci", "tr", "dma", "pdi", "mdi", "adx", "adxr", "trix",
          "tema", "vr", "dpo", "ppo", "stochrsi", "wt1", "wt2", "supertrend", "aroon", "z", "ao", "bop",
          "cmo", "ker", "kama", "chop", "eribull", "eribear", "ftr", "rvgi", "inertia", "kst", "pgo",
          "psl", "pvo", "qqe", "cti", "lrma", "close_-1_d", "close_2_r", "change"]


def value(d, name):
    s = wrap(d.copy())
    return s[name]


print(f"{'indicator':14s} {'used by TradingAgents':>22s} {'result':>24s}")
for name in USED_BY_TRADINGAGENTS + OTHERS:
    try:
        full = value(df, name)
    except Exception as e:
        print(f"{name:14s} {'':>22s} {'not available':>24s}")
        continue
    bad = seen = 0
    for k in cuts:
        a = full.iloc[k]
        b = value(df.iloc[: k + 1], name).iloc[-1]
        if pd.isna(a) and pd.isna(b):
            continue
        seen += 1
        if pd.isna(a) != pd.isna(b) or not np.isclose(a, b, rtol=1e-6, atol=1e-9):
            bad += 1
    tag = "yes" if name in USED_BY_TRADINGAGENTS else ""
    res = f"LEAKS ({bad}/{seen} cuts)" if bad else "clean"
    print(f"{name:14s} {tag:>22s} {res:>24s}")
