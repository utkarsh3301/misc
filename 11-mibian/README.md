# 11. mibian (options pricing and implied volatility)

Repo: https://github.com/yassinemaaroufi/MibianLib
Studied: shallow clone of `master` (last commit June 2021).

## What it is

A small pure-Python options library: Black-Scholes (`BS`), Garman-Kohlhagen for FX (`GK`) and
Merton with dividends (`Me`), each returning prices, greeks and implied volatility. It is
commonly used in retail options scripts, including NIFTY and BANKNIFTY option-chain dashboards
and IV-based strategies.

## How it works (from the source, `mibian/__init__.py`)

| Piece | Detail |
|---|---|
| Inputs | `BS([spot, strike, rate_in_percent, calendar_days], volatility=percent)`. Rate and vol are percents; time is calendar days / 365. |
| Greeks | Theta is per calendar day (divided by 365), vega and rho per 1 percentage point (divided by 100). |
| Implied vol | Bisection between 0% and 500%, stopping when `round(estimate, decimals) == target`, where `decimals` is the number of digits after the point in `str(price)`. |
| Guards | If the call price is below `spot - strike`, it returns 0.001 (a 0.001% vol). If the price is above the 500%-vol price, it returns 500. |

## Where the edge is supposed to come from

None, it is a pricing tool. The question is whether the implied vols it reports can be trusted,
because IV-based option strategies are only as good as the IV they read.

## What I found

**1. Mostly accurate on NIFTY-style weeklies.** I priced a grid of out-of-the-money weekly options
like NIFTY (spot 24000, strikes every 50 points within +/-5%, 1 to 7 days, rate 6.5%, true vols
10% to 25%), rounded each premium to the 0.05 tick, and backed out IV with mibian and with an
exact solver on the same rounded price:

| Source of IV error (vol points) | Median | 95th percentile | Max |
|---|---|---|---|
| The 0.05 tick itself (exact solver) | 0.003 | 0.109 | |
| Extra error from mibian's stopping rule | 0.002 | 0.052 | 0.87 |

No exceptions in 1,222 options, and no case more than 1 vol point off. The tick is a bigger
source of error than the library.

**2. The stopping rule depends on how the price is written.** Because the tolerance comes from
`str(price)`, a premium of 0.10 is read as `'0.1'`: one decimal, so any estimate between 0.05
and 0.15 counts as a match. That is where the worst cases come from: cheap far out-of-the-money
options at 0.10, off by 0.5 to 0.9 vol points (for example, true 20.4% read as 19.5%). The same
premium passed as 0.1 or as 0.10 gives the same string, so you cannot fix it from the outside
except by solving IV yourself. The error is largest at 1 day to expiry (95th percentile 0.17 vol
points), exactly where weekly sellers look hardest.

**3. Bad inputs fail silently.**
- An in-the-money call quoted below the no-arbitrage floor returns an implied vol of 0.00001% or
  0.001% instead of an error. A stale or crossed quote becomes a "zero-vol" data point.
- `volatility=0` is ignored because 0 is falsy in Python: the object is built with no prices at
  all (`callPrice` is `None`), again without an error.

**4. Conventions to remember.** Time is calendar days / 365. On expiry day `days=0` raises
`ZeroDivisionError`, and an option at 9:15 am on its last day is priced as if it had a full day
left unless you pass a fraction such as 0.26. Theta is per calendar day.

## The edge, in one line

No edge, and no hidden one: a usable Black-Scholes calculator whose IVs are good to about 0.1
vol point on normal weekly strikes. Watch cheap 0.10-premium strikes, expiry-day time handling
and silent failures on bad quotes.

## Takeaways for our own work

- For IV surfaces or skew signals on NIFTY weeklies, use an exact root-finder (Brent) and pass
  time in fractions of a year including intraday hours.
- Filter quotes that violate no-arbitrage bounds before solving, instead of letting the solver
  return a tiny vol.
- Remember the 0.05 tick alone can move short-dated far-OTM IV by about 0.1 vol point. Signals
  smaller than that are noise.

## Reproduce

```
git clone --depth 1 https://github.com/yassinemaaroufi/MibianLib
PYTHONPATH=./MibianLib python experiments/iv_solver_accuracy.py
```

`pip install mibian` failed to build on Python 3.13 here; the library is a single pure-Python
file, so the clone on `PYTHONPATH` works.
