"""What did the 2014-2018 VIX sample not see? Realized-volatility regimes in 1999-2018 S&P 500 data.

Run from the repo root:
    PYTHONPATH=. python3 scripts/run_tail_frequency.py

Real data only: S&P 500 daily closes 1999-2018 bundled in the arch package.
Implied volatility is not available before 2014 in this environment, so this
script says nothing about the VIX level in earlier years. It measures how
extreme realized 21-day volatility and returns were, and compares the 2014-2018
window used in the premium study to the full 20 years.

The final table is plain arithmetic, not data: the payoff of a short variance
position per unit of strike variance for chosen (strike VIX, realized vol) pairs.
"""
import json
import os

import numpy as np
import pandas as pd
from arch.data import sp500

OUT = "results"
W = 21


def main():
    os.makedirs(OUT, exist_ok=True)
    spx = sp500.load()["Close"]
    logp = np.log(spx)
    r = logp.diff()
    fwd_rv_vol = 100.0 * np.sqrt((252.0 / W) * (r ** 2).rolling(W).sum().shift(-W))
    fwd_ret = logp.shift(-W) - logp
    d = pd.concat([fwd_rv_vol.rename("rv_vol"), fwd_ret.rename("ret")], axis=1).dropna()

    full = d
    sub = d.loc["2014-01-01":"2018-11-30"]
    res = {"full": {"start": str(full.index[0].date()), "end": str(full.index[-1].date()), "n": int(len(full))},
           "sub": {"start": str(sub.index[0].date()), "end": str(sub.index[-1].date()), "n": int(len(sub))}}

    print("== forward 21-day realized volatility (annualized vol points)")
    for name, x in [("1999-2018", full), ("2014-2018", sub), ("1999-2013", d.loc[:"2013-12-31"])]:
        q = x["rv_vol"].quantile([0.5, 0.9, 0.99])
        print(f"  {name}: mean {x['rv_vol'].mean():.1f}  median {q[0.5]:.1f}  p90 {q[0.9]:.1f}  p99 {q[0.99]:.1f}  max {x['rv_vol'].max():.1f}")
        res[name] = {"mean": float(x["rv_vol"].mean()), "median": float(q[0.5]), "p90": float(q[0.9]), "p99": float(q[0.99]), "max": float(x["rv_vol"].max())}

    print("\n== share of windows with realized vol at or above a level")
    levels = [15, 20, 25, 30, 40, 50, 60]
    rows = []
    for L in levels:
        rows.append(
            {
                "rv_vol_at_least": L,
                "share_1999_2018": float((full["rv_vol"] >= L).mean()),
                "share_2014_2018": float((sub["rv_vol"] >= L).mean()),
                "share_1999_2013": float((d.loc[:"2013-12-31", "rv_vol"] >= L).mean()),
            }
        )
    t1 = pd.DataFrame(rows).set_index("rv_vol_at_least")
    print(t1.round(3).to_string())
    res["share_by_level"] = t1.round(4).to_dict(orient="index")

    print("\n== distinct episodes with realized vol >= 40 (start dates less than 21 trading days apart merged)")
    hot = d.index[d["rv_vol"] >= 40]
    episodes = []
    for dt in hot:
        if episodes and (d.index.get_loc(dt) - d.index.get_loc(episodes[-1][1])) <= W:
            episodes[-1][1] = dt
        else:
            episodes.append([dt, dt])
    for a, b in episodes:
        peak = d.loc[a:b, "rv_vol"].max()
        print(f"  {a.date()} to {b.date()}  peak realized vol {peak:.0f}")
    res["episodes_rv40"] = [[str(a.date()), str(b.date()), float(d.loc[a:b, 'rv_vol'].max())] for a, b in episodes]

    print("\n== break-even strike for a short variance seller: sqrt of the mean forward realized variance (vol points)")
    var_w = (d["rv_vol"] / 100.0) ** 2
    subsets = {
        "1999-2018": var_w,
        "1999-2013": var_w.loc[:"2013-12-31"],
        "2014-2018": var_w.loc["2014-01-01":"2018-11-30"],
        "2008-2009 only": var_w.loc["2008-01-01":"2009-12-31"],
        "excluding 2008-2009": var_w.loc[~var_w.index.year.isin([2008, 2009])],
    }
    be = {}
    for name, x in subsets.items():
        mean_vol = float((100.0 * np.sqrt(x)).mean())
        strike = float(100.0 * np.sqrt(x.mean()))
        be[name] = {"mean_realized_vol": mean_vol, "breakeven_strike": strike, "n": int(len(x))}
        print(f"  {name:22s} mean realized vol {mean_vol:6.2f}   break-even strike {strike:6.2f}   (n={len(x)})")
    res["breakeven_strike"] = be

    print("\n== mean 21-day realized volatility by five-year block (trailing windows, calendar-year blocks)")
    rv_tr = (100.0 * np.sqrt((252.0 / W) * (r ** 2).rolling(W).sum())).dropna()
    blocks = pd.Series({y: float(rv_tr.loc[f"{y}-01-01":f"{y + 4}-12-31"].mean()) for y in range(1999, 2015)}).sort_values()
    rank = list(blocks.index).index(2014) + 1
    for y, v in blocks.items():
        print(f"  {y}-{y + 4}: {v:6.2f}" + ("   <- the premium-test window" if y == 2014 else ""))
    print(f"  rank of 2014-2018 (1 = calmest): {rank} of {len(blocks)}")
    res["five_year_blocks"] = {"mean_by_start_year": {str(k): v for k, v in blocks.items()}, "rank_of_2014_block": rank, "n_blocks": int(len(blocks))}

    print("\n== 21-day S&P 500 log return: frequency of declines")
    rows = []
    for thr in [-0.05, -0.10, -0.15, -0.20]:
        rows.append(
            {
                "return_at_or_below": thr,
                "share_1999_2018": float((full["ret"] <= thr).mean()),
                "share_2014_2018": float((sub["ret"] <= thr).mean()),
            }
        )
    t2 = pd.DataFrame(rows).set_index("return_at_or_below")
    print(t2.round(3).to_string())
    res["share_by_decline"] = t2.round(4).to_dict(orient="index")
    print(f"  worst 21-day log return: 1999-2018 {full['ret'].min():.3f}  2014-2018 {sub['ret'].min():.3f}")
    res["worst_21d_log_return"] = {"1999-2018": float(full["ret"].min()), "2014-2018": float(sub["ret"].min())}

    print("\n== arithmetic grid (not data): short variance payoff per unit strike variance = 1 - (RV/VIX)^2, uncapped")
    vix_levels = [12, 15, 20, 25]
    rv_levels = [10, 15, 20, 30, 40, 60, 80]
    grid = pd.DataFrame({f"VIX {v}": [1 - (rv / v) ** 2 for rv in rv_levels] for v in vix_levels}, index=[f"RV {rv}" for rv in rv_levels])
    print(grid.round(2).to_string())
    res["payoff_grid_arithmetic"] = grid.round(3).to_dict(orient="index")

    with open(os.path.join(OUT, "tail_frequency.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("\nsaved results/tail_frequency.json")


if __name__ == "__main__":
    main()
