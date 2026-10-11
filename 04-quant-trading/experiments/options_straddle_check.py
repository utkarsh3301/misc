"""
Re-run the repo's long straddle on its own STOXX 50 data (data/stoxx50.xlsx, Aug 2019 expiry).

The repo computes, for each strike:
    profit = |spot_T * contractsize - strike * contractsize| - call - put
Spot and strike are scaled by the contract size (10 EUR per index point), the premiums are not,
although they are quoted in index points too. It also loops over every strike and the comments
describe picking the one that maximises profit, i.e. choosing the strike after seeing expiry.

Usage: python options_straddle_check.py /path/to/quant-trading
"""
import importlib.util
import os
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
REPO = Path(sys.argv[1])
os.chdir = lambda *_: None  # the script does os.chdir('d:/') at import time
spec = importlib.util.spec_from_file_location("straddle", REPO / "Options Straddle backtest.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

x = pd.ExcelFile(REPO / "data" / "stoxx50.xlsx")
aug = x.parse("aug").set_index("Dates")
spot = x.parse("spot").set_index("Dates")
aug.index, spot.index = pd.to_datetime(aug.index), pd.to_datetime(spot.index)
CS, TH = 10, 2

rows = []
for k in sorted(m.find_strike_price(aug)):
    df = m.signal_generation(m.straddle(aug, spot, CS, k), TH)
    ind = df[df["signals"] != 0].index
    if ind.empty:
        rows.append((k, None, None, None, None))
        continue
    entry = ind[0]
    prem = df["call"][entry] + df["put"][entry]
    payoff = abs(df["spot"].iloc[-1] - int(k) * CS)
    rows.append((k, entry.date(), prem, payoff - prem, payoff - prem * CS))
t = pd.DataFrame(rows, columns=["strike", "entry", "premium_pts", "pnl_as_repo_eur", "pnl_premium_scaled_eur"])
print(t.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
traded = t.dropna()
print(f"\nStrikes with a trade: {len(traded)}. Profitable as repo computes it: {(traded.pnl_as_repo_eur > 0).sum()}."
      f" Profitable with premiums in the same units: {(traded.pnl_premium_scaled_eur > 0).sum()}.")
