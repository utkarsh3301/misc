"""
Stress-test three strategies from je-suis-tm/quant-trading on ~300 CSI300 stocks, 2008-2021.

For each one we keep the repo's signal logic and change only how the trade is filled:
  as_repo : the way the repo's backtest does it
  honest  : no information from the future, fill on the next bar, 0.1% cost per side

1. Heikin-Ashi:  repo buys/sells at the same Close that produced the signal, no costs.
2. MACD (MA cross, 10/21): same-close fill, no costs in the repo.
3. Dual Thrust: the repo's range uses a rolling window that INCLUDES the current day's
   high/low/close (intraday['range'][date] is computed with rolling(rg) on a frame indexed
   by that same date). We rebuild it on daily bars: enter on a break of open +/- k*range,
   exit at the close, with the range window either including today (as repo) or ending yesterday.

Usage: python execution_and_lookahead.py /path/to/qlib_data/cn
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
F = {f: pd.DataFrame({c: read(c, f) for c in codes}).loc["2008-01-01":"2021-06-01"] for f in ["open", "high", "low", "close"]}
O, H, L, C = F["open"], F["high"], F["low"], F["close"]
COST = 0.001


def summarise(daily, name):
    d = daily.mean(axis=1).dropna()
    ann = d.mean() * 252
    sr = d.mean() / d.std() * np.sqrt(252) if d.std() > 0 else np.nan
    return f"{name:44s} ann {ann:+7.1%}   Sharpe {sr:+5.2f}"


# ---------- 1. Heikin-Ashi (repo logic, stls=3 units max) ----------
def ha_positions(o, h, l, c, stls=3):
    hac = (o + h + l + c) / 4
    hao = np.empty_like(hac)
    hao[0] = o[0]
    for n in range(1, len(hac)):
        hao[n] = (hao[n - 1] + hac[n - 1]) / 2
    hah = np.maximum.reduce([hao, hac, h])
    hal = np.minimum.reduce([hao, hac, l])
    pos, units = np.zeros(len(c)), 0
    for n in range(1, len(c)):
        if np.isnan(hac[n]) or np.isnan(hac[n - 1]):
            pos[n] = units
            continue
        if (hao[n] > hac[n] and hao[n] == hah[n] and abs(hao[n] - hac[n]) > abs(hao[n - 1] - hac[n - 1])
                and hao[n - 1] > hac[n - 1]):
            if units < stls:
                units += 1
        elif hao[n] < hac[n] and hao[n] == hal[n] and hao[n - 1] < hac[n - 1]:
            units = 0
        pos[n] = units
    return pos / stls


ret = C.pct_change(fill_method=None)
ha_pos = pd.DataFrame({c: ha_positions(*(F[f][c].values for f in ["open", "high", "low", "close"])) for c in codes},
                      index=C.index)
ha_repo = ha_pos.shift(1) * ret                              # filled at signal close, no cost
# honest: signal known at close t, position held from open t+1 to open t+2, cost on changes
oo = O.shift(-1) / O - 1  # open t to open t+1
ha_honest = (ha_pos.shift(1) * oo - ha_pos.shift(1).diff().abs() * COST).shift(1)

# ---------- 2. MACD / MA cross 10-21, long only ----------
ma1, ma2 = C.rolling(10, min_periods=1).mean(), C.rolling(21, min_periods=1).mean()
mpos = (ma1 >= ma2).astype(float).where(C.notna())
macd_repo = mpos.shift(1) * ret
mlive = mpos.shift(1)
macd_honest = (mlive * oo - mlive.diff().abs() * COST).shift(1)
bh = ret

# ---------- 3. Dual Thrust on daily bars, k = 0.5, range window 4 days ----------
def dual_thrust(include_today, k=0.5, rg=4):
    if include_today:   # what the repo effectively does
        hh, lc, hc, ll = H.rolling(rg).max(), C.rolling(rg).min(), C.rolling(rg).max(), L.rolling(rg).min()
    else:
        hh, lc, hc, ll = (x.shift(1) for x in (H.rolling(rg).max(), C.rolling(rg).min(), C.rolling(rg).max(), L.rolling(rg).min()))
    rng = np.maximum(hh - lc, hc - ll)
    up, dn = O + k * rng, O - (1 - k) * rng
    long_hit, short_hit = H > up, L < dn
    pnl = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    only_long = long_hit & ~short_hit
    only_short = short_hit & ~long_hit
    both = long_hit & short_hit
    pnl[only_long] = (C / up - 1)[only_long]
    pnl[only_short] = (dn / C - 1)[only_short]
    # both bands hit: assume long first, stopped and reversed at the lower band, short to close
    pnl[both] = ((dn / up - 1) + (dn / C - 1))[both]
    trades = only_long.astype(int) + only_short.astype(int) + 2 * both.astype(int)
    pnl = pnl - trades * 2 * COST
    return pnl.where(C.notna()), (long_hit | short_hit).mean().mean()


print("Equal-weight across ~300 CSI300 names, 2008-2021, daily rebalanced\n")
print(summarise(bh, "Buy and hold (reference)"))
print()
print(summarise(ha_repo, "Heikin-Ashi, as repo (same close, no cost)"))
print(summarise(ha_honest, "Heikin-Ashi, honest (next open, 0.1%/side)"))
print()
print(summarise(macd_repo, "MA cross 10/21, as repo (same close, no cost)"))
print(summarise(macd_honest, "MA cross 10/21, honest (next open, cost)"))
print()
dt_repo, f1 = dual_thrust(True)
dt_fix, f2 = dual_thrust(False)
print(summarise(dt_repo, "Dual Thrust, range includes today (as repo)"))
print(summarise(dt_fix, "Dual Thrust, range ends yesterday (fixed)"))
print(f"  share of stock-days with a trade: repo {f1:.0%}, fixed {f2:.0%}")
print("\nNote: Dual Thrust here is a day trade, which A-share T+1 rules do not allow for new buys;"
      " treat it as a test of the backtest logic, not a tradable China strategy.")

# Where does the MA-cross Sharpe edge over buy-and-hold come from? Year by year, honest version.
yr = pd.DataFrame({"buy_hold": bh.mean(axis=1), "ma_cross_honest": macd_honest.mean(axis=1)}).dropna()
by_year = yr.groupby(yr.index.year).sum()
print("\nCalendar-year return (sum of daily, equal weight):")
print(by_year.to_string(float_format=lambda x: f"{x:+.0%}"))
ex = yr[~yr.index.year.isin([2008, 2015])]
s = lambda d: d.mean() / d.std() * np.sqrt(252)
print(f"\nSharpe excluding 2008 and 2015: buy-and-hold {s(ex.buy_hold):+.2f}, MA cross honest {s(ex.ma_cross_honest):+.2f}")
