"""
How accurate is mibian's implied volatility on NIFTY-style weekly options?

mibian (https://github.com/yassinemaaroufi/MibianLib) is a small Black-Scholes library that is
very common in Indian options-trading tutorials. Its impliedVolatility() bisects until
    round(estimate, decimals) == target
where `decimals` is the number of digits after the point in str(price). So a premium quoted as
120.5 is matched only to 0.05, and 120.0 only to the nearest 0.1.

We build a grid like NIFTY weekly options (spot 24000, strikes every 50 points within +/-5%,
1 to 7 calendar days, rate 6.5%, true vols 10% to 25%), price them exactly, round to the 0.05 tick
the exchange quotes, and back out IV two ways:
  mibian   mibian.BS(..., callPrice=p / putPrice=p).impliedVolatility
  exact    Brent's method to 1e-10 on the same rounded price
The difference between "exact" and the true vol is the unavoidable tick error; the difference
between mibian and "exact" is what the library adds.

Usage: python iv_solver_accuracy.py      (put a clone of MibianLib on PYTHONPATH)
"""
import math
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

import mibian

warnings.filterwarnings("ignore")
S, R = 24000.0, 6.5


def bs(S, K, r, days, vol, call=True):
    T, r, v = days / 365, r / 100, vol / 100
    d1 = (math.log(S / K) + (r + v * v / 2) * T) / (v * math.sqrt(T))
    d2 = d1 - v * math.sqrt(T)
    if call:
        return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


rows = []
for days in range(1, 8):
    for K in np.arange(22800, 25201, 50):
        for vol in (10, 15, 20, 25):
            for call in (True, False):
                otm = (K >= S) if call else (K <= S)
                if not otm:  # traders read IV off the out-of-the-money side
                    continue
                p = round(bs(S, K, R, days, vol, call) / 0.05) * 0.05
                p = round(p, 2)
                if p < 0.05:
                    continue
                try:
                    exact = brentq(lambda v: bs(S, K, R, days, v, call) - p, 0.01, 500, xtol=1e-10)
                except ValueError:
                    exact = np.nan
                try:
                    m = mibian.BS([S, K, R, days], **({"callPrice": p} if call else {"putPrice": p}))
                    mib = m.impliedVolatility
                    err = None
                except Exception as e:
                    mib, err = np.nan, type(e).__name__
                rows.append(dict(days=days, K=K, vol=vol, call=call, price=p, exact=exact, mibian=mib, error=err))

t = pd.DataFrame(rows)
t["tick_err"] = (t.exact - t.vol).abs()
t["mibian_extra"] = (t.mibian - t.exact).abs()
ok = t.dropna(subset=["mibian", "exact"])
print(f"Options in grid: {len(t)} (out-of-the-money, premium >= 0.05)")
print(f"mibian raised an exception on {t.error.notna().sum()} ({t.error.notna().mean():.1%}): {t.error.dropna().value_counts().to_dict()}")
print(f"\nIV error in vol points (e.g. 0.5 = 15.0% read as 15.5%):")
print(f"  from the 0.05 tick alone (exact solver): median {ok.tick_err.median():.3f}, 95th pct {ok.tick_err.quantile(.95):.3f}")
print(f"  added by mibian's stopping rule:        median {ok.mibian_extra.median():.3f}, 95th pct {ok.mibian_extra.quantile(.95):.3f}, max {ok.mibian_extra.max():.2f}")
whole = ok[ok.price.map(lambda x: float(x).is_integer())]
print(f"  on premiums that are whole numbers (str(120.0) has 1 decimal): median extra {whole.mibian_extra.median():.3f}, 95th pct {whole.mibian_extra.quantile(.95):.3f} (n={len(whole)})")
print("\nBy days to expiry, 95th percentile of mibian's extra error (vol points):")
print(ok.groupby("days").mibian_extra.quantile(.95).round(3).to_string())
bad = ok[ok.mibian_extra > 1]
print(f"\nShare of options where mibian is off by more than 1 vol point: {len(bad) / len(ok):.1%}")
print("\nWorst cases:")
print(ok.nlargest(5, "mibian_extra")[["days", "K", "call", "vol", "price", "exact", "mibian"]].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# Edge cases straight from the code
print("\nEdge cases:")
c = mibian.BS([24000, 23000, 6.5, 30], callPrice=1000.0)  # below the no-arbitrage floor
print(f"  ITM call quoted at 1000.0 (no-arbitrage floor S - K*exp(-rT) is about {24000 - 23000*math.exp(-0.065*30/365):.0f}): IV returned {c.impliedVolatility}")
c = mibian.BS([24000, 23000, 6.5, 30], callPrice=999.0)
print(f"  same call quoted at 999.0 (below S - K): IV returned {c.impliedVolatility} (silently a 0.001% vol)")
c = mibian.BS([24000, 24000, 6.5, 7], volatility=0)
print(f"  volatility=0 passed explicitly: callPrice = {c.callPrice} (0 is falsy, so the input is ignored and nothing is computed)")
