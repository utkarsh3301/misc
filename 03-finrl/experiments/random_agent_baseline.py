"""
How much of a FinRL "agent beats the index" result is the agent, and how much is the setup?

This is a line-by-line port of the trading mechanics in FinRL's
finrl/meta/env_stock_trading/env_stocktrading.py (StockTradingEnv.step, _buy_stock, _sell_stock):
  - action in [-1, 1] per stock, multiplied by hmax and truncated to whole shares
  - sells processed first (clipped to shares held), then buys (clipped to cash)
  - 0.1% cost on both sides, trades at the same close the agent observed
It then runs agents that know nothing at all:
  - random:      uniform random actions every day
  - always_buy:  action +1 every day
and compares them with equal-weight buy-and-hold over many windows the same length as
FinRL's flagship tutorial test window (2020-07-01 to 2021-10-29, about 335 trading days).

Data: 30 large CSI300 stocks from qlib's public CN dataset (any daily panel works).
Usage: python random_agent_baseline.py /path/to/qlib_data/cn
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
closes = pd.DataFrame({c: read_close(c) for c in codes}).loc["2008-01-01":"2021-06-01"]
# 30 names with the most complete history (stand-in for the Dow 30 used in FinRL tutorials)
pick = closes.notna().sum().sort_values(ascending=False).index[:30]
px = closes[pick].ffill().dropna()

HMAX, COST, CASH0, WIN = 100, 0.001, 1_000_000.0, 335


def run(prices, policy, rng):
    n = prices.shape[1]
    cash, shares = CASH0, np.zeros(n)
    for t in range(len(prices) - 1):
        p = prices[t]
        a = policy(rng, n)
        a = (a * HMAX).astype(int)
        order = np.argsort(a)
        for i in order[: (a < 0).sum()]:  # sells first, clipped to holdings
            q = min(-a[i], shares[i])
            cash += p[i] * q * (1 - COST)
            shares[i] -= q
        for i in order[::-1][: (a > 0).sum()]:  # then buys, clipped to cash
            q = min(cash // (p[i] * (1 + COST)), a[i])
            cash -= p[i] * q * (1 + COST)
            shares[i] += q
    final = cash + (shares * prices[-1]).sum()
    exposure = (shares * prices[-1]).sum() / final
    return final / CASH0 - 1, exposure


policies = {
    "random": lambda rng, n: rng.uniform(-1, 1, n),
    "always_buy": lambda rng, n: np.ones(n),
}

rows = []
starts = range(0, len(px) - WIN, 60)
for s in starts:
    w = px.iloc[s : s + WIN]
    prices = (w / w.iloc[0] * 100).values  # each stock starts at 100, so hmax=100 means up to 10k per name per day
    bh = (w.iloc[-1] / w.iloc[0]).mean() - 1
    rng = np.random.default_rng(s)
    rand = [run(prices, policies["random"], rng) for _ in range(20)]
    ab, ab_exp = run(prices, policies["always_buy"], rng)
    rows.append(dict(start=w.index[0].date(), buy_hold=bh,
                     random_median=np.median([r[0] for r in rand]),
                     random_best=np.max([r[0] for r in rand]),
                     random_end_exposure=np.median([r[1] for r in rand]),
                     always_buy=ab))
res = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(res.to_string(index=False, float_format=lambda x: f"{x:+.1%}"))

beat = (res.random_best > res.buy_hold).mean()
print(f"\nWindows: {len(res)}")
print(f"Best of 20 random agents beats equal-weight buy-and-hold in {beat:.0%} of windows")
print(f"Correlation of random-agent median return with buy-and-hold across windows: {res.random_median.corr(res.buy_hold):.2f}")
print(f"Median end-of-window stock exposure of random agents: {res.random_end_exposure.median():.0%} (they drift long)")
print(f"Spread between best and worst window for buy-and-hold: {res.buy_hold.min():+.0%} to {res.buy_hold.max():+.0%}")
