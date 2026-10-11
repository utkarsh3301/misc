"""
Do Vibe-Trading's "Shadow Account" bias detectors flag traders who have no biases at all?

We import the real detectors from HKUDS/Vibe-Trading (agent/src/tools/trade_journal_tool.py:
_compute_behavior -> disposition_effect, overtrading, chasing_momentum, anchoring) and feed them
trade journals written by emotionless robots on real CSI300 price paths:

  sip         buys 100 shares every 20 trading days for a year, sells everything at the end
              (a monthly SIP: zero discretion, zero emotion)
  coin_flip   enters at random, always exits exactly 10 trading days later
              (holding time cannot depend on win or loss)
  bracket     enters at random, exits at +5% take-profit or -15% stop-loss
              (a written rule, decided before entry)

A good detector should rarely flag the first two. We report the share of robot accounts
rated medium or high for each bias.

Usage:
  python robot_traders_vs_bias_detectors.py /path/to/Vibe-Trading /path/to/qlib_data/cn
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

VT, DATA = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(VT / "agent"))
from src.tools.trade_journal_tool import _compute_behavior  # noqa: E402

cal = pd.to_datetime(pd.read_csv(DATA / "calendars/day.txt", header=None)[0])


def read_close(code):
    a = np.fromfile(DATA / "features" / code / "close.day.bin", dtype="<f4")
    return pd.Series(a[1:], index=cal[int(a[0]) : int(a[0]) + len(a) - 1].values).dropna()


codes = sorted(p.name for p in (DATA / "features").iterdir() if p.name.startswith(("sh60", "sz00")))
rng = np.random.default_rng(7)


def row(dt, sym, side, px, qty=100):
    return dict(datetime=pd.Timestamp(dt), symbol=sym, side=side, price=float(px), quantity=qty, fee=0.0, market="a_share")


def sip(sym, s):
    i0 = rng.integers(0, len(s) - 260)
    w = s.iloc[i0 : i0 + 252]
    rows = [row(w.index[k], sym, "buy", w.iloc[k]) for k in range(0, 240, 20)]
    rows.append(row(w.index[-1], sym, "sell", w.iloc[-1], qty=100 * len(rows)))
    return rows


def coin_flip(sym, s):
    rows, k = [], int(rng.integers(0, 50))
    while k + 10 < len(s) and len(rows) < 60:
        if rng.random() < 0.1:
            rows += [row(s.index[k], sym, "buy", s.iloc[k]), row(s.index[k + 10], sym, "sell", s.iloc[k + 10])]
            k += 11
        else:
            k += 1
    return rows


def bracket(sym, s):
    rows, k = [], int(rng.integers(0, 50))
    while k < len(s) - 1 and len(rows) < 60:
        if rng.random() < 0.1:
            entry = s.iloc[k]
            j = k + 1
            while j < len(s) - 1 and -0.15 < s.iloc[j] / entry - 1 < 0.05:
                j += 1
            rows += [row(s.index[k], sym, "buy", entry), row(s.index[j], sym, "sell", s.iloc[j])]
            k = j + 1
        else:
            k += 1
    return rows


robots = {"sip": sip, "coin_flip": coin_flip, "bracket": bracket}
sample = rng.choice(codes, size=120, replace=False)
results = {name: [] for name in robots}
for sym in sample:
    s = read_close(sym).loc["2010-01-01":]
    if len(s) < 600:
        continue
    for name, robot in robots.items():
        rows = robot(sym, s)
        if len(rows) < 4:
            continue
        df = pd.DataFrame(rows).sort_values("datetime").reset_index(drop=True)
        b = _compute_behavior(df)
        results[name].append({k: v.get("severity", "low") for k, v in b.items() if isinstance(v, dict)})

print("Share of robot accounts flagged medium or high, by detector (one account = one stock):\n")
print(f"{'robot':10s} {'accounts':>8s} {'disposition':>12s} {'overtrading':>12s} {'chasing':>9s} {'anchoring':>10s}")
for name, rs in results.items():
    df = pd.DataFrame(rs)
    flag = lambda c: (df[c].isin(["medium", "high"])).mean() if c in df else float("nan")
    print(f"{name:10s} {len(df):8d} {flag('disposition_effect'):12.0%} {flag('overtrading'):12.0%} "
          f"{flag('chasing_momentum'):9.0%} {flag('anchoring'):10.0%}")
