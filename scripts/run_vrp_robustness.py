"""Robustness checks on the real-data variance risk premium result.

Run from the repo root:
    PYTHONPATH=. python3 scripts/run_vrp_robustness.py

Covers: selling cost sensitivity, a null-hypothesis bootstrap p-value, a
leverage and drawdown view, a market-plus-convexity alpha regression, and
sensitivity to the window length.
"""
import json
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import brentq

from src import stats_utils as su
from src import vrp

OUT = "results"
RNG = np.random.default_rng(20261012)
WINDOW = 21
PPY = 252.0 / WINDOW


def hac(y, X, lags):
    return sm.OLS(y, sm.add_constant(X), missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": lags})


payoff_with_cost = vrp.payoff_with_cost


def stationary_bootstrap_means(x, mean_block, reps, rng):
    n = len(x)
    p = 1.0 / mean_block
    means = np.empty(reps)
    for r in range(reps):
        idx = np.empty(n, dtype=np.int64)
        idx[0] = rng.integers(n)
        jumps = rng.random(n) < p
        starts = rng.integers(n, size=n)
        for t in range(1, n):
            idx[t] = starts[t] if jumps[t] else (idx[t - 1] + 1) % n
        means[r] = x[idx].mean()
    return means


def null_pvalue(s, reps, mean_block=3):
    x = np.asarray(s, dtype=float)
    obs = x.mean()
    bm = stationary_bootstrap_means(x - obs, mean_block, reps, RNG)
    return float((bm >= obs).mean())


def leverage_table(s, targets=(0.05, 0.10, 0.15, 0.20, 0.30)):
    sd_ann = s.std(ddof=1) * np.sqrt(PPY)
    rows = []
    for tgt in targets:
        scale = tgt / sd_ann
        r = np.maximum(scale * s.values, -1.0)
        eq = np.cumprod(1.0 + r)
        peak = np.maximum.accumulate(eq)
        mdd = float((eq / peak - 1.0).min())
        years = len(r) / PPY
        cagr = float(eq[-1] ** (1.0 / years) - 1.0) if eq[-1] > 0 else -1.0
        rows.append(
            {
                "target_vol": tgt,
                "scale_on_unit_notional": float(scale),
                "worst_month": float(r.min()),
                "max_drawdown": mdd,
                "cagr": cagr,
                "final_equity": float(eq[-1]),
            }
        )
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    res = {}
    df = vrp.add_payoffs(vrp.load_frame(WINDOW)).dropna(subset=["vix"])
    d = df.dropna(subset=["rv_fwd"]).copy()

    print("== A. cost sensitivity: sell at (VIX - c) vol points")
    rows = []
    for c in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        row = {"c_volpts": c}
        for kind in ["var", "vol"]:
            full = payoff_with_cost(d, c, kind)
            shs = []
            for off in range(WINDOW):
                sub = full.reindex(vrp.nonoverlap(df, WINDOW, off).index).dropna()
                shs.append(sub.mean() / sub.std(ddof=1) * np.sqrt(PPY))
            row[f"{kind}_mean"] = float(full.mean())
            row[f"{kind}_sharpe"] = float(np.mean(shs))
            row[f"{kind}_t_nw"] = su.newey_west_t(full, WINDOW - 1)
        rows.append(row)
    tabA = pd.DataFrame(rows).set_index("c_volpts")
    print(tabA.round(3).to_string())
    be = {}
    for kind in ["var", "vol"]:
        f = lambda c: payoff_with_cost(d, c, kind).mean()
        be[kind] = float(brentq(f, 0.0, 13.0))
    print("  break-even cost (vol points of selling concession) where mean payoff = 0:", {k: round(v, 2) for k, v in be.items()})
    res["cost_table"] = tabA.round(4).to_dict(orient="index")
    res["breakeven_cost_volpts"] = be

    print("\n== B. null-hypothesis bootstrap p-values (stationary bootstrap, mean block 3 months, demeaned null)")
    pv = {}
    for kind, col in [("var", "R_var"), ("vol", "R_vol")]:
        p0 = null_pvalue(vrp.nonoverlap(df, WINDOW, 0)[col].dropna(), reps=20000)
        others = [null_pvalue(vrp.nonoverlap(df, WINDOW, off)[col].dropna(), reps=3000) for off in range(1, WINDOW)]
        pv[kind] = {"offset0": p0, "median_other_offsets": float(np.median(others)), "max_other_offsets": float(np.max(others))}
        print(f"  {kind}: offset0 p={p0:.4f}  median over other offsets p={np.median(others):.4f}  worst offset p={np.max(others):.4f}")
    res["null_bootstrap_pvalues"] = pv

    print("\n== C. leverage view on the offset-0 monthly series (compounded, no costs, hold to expiry)")
    m0 = vrp.nonoverlap(df, WINDOW, 0)
    lev = {}
    for col in ["R_var", "R_vol"]:
        s = m0[col].dropna()
        pay = float(s.min() / s.mean())
        print(f"  {col}: worst window = {s.min():.2f}, mean = {s.mean():.3f}, months of average gains erased by the worst window = {abs(pay):.1f}")
        t = leverage_table(s)
        print(t.round(3).to_string(index=False))
        lev[col] = {"months_of_mean_gain_lost_in_worst_window": abs(pay), "table": t.round(4).to_dict(orient="records")}
    res["leverage_view"] = lev

    print("\n== D. alpha after market and convexity controls (all daily windows, HAC 20 lags)")
    mk = {}
    for col in ["R_var", "R_vol"]:
        X1 = d[["ret_fwd"]]
        X2 = pd.concat([d["ret_fwd"], d["ret_fwd"] ** 2], axis=1)
        X2.columns = ["mkt", "mkt_sq"]
        m1 = hac(d[col], X1, 20)
        m2 = hac(d[col], X2, 20)
        mk[col] = {
            "alpha_linear": float(m1.params["const"]),
            "alpha_linear_t": float(m1.tvalues["const"]),
            "alpha_quadratic": float(m2.params["const"]),
            "alpha_quadratic_t": float(m2.tvalues["const"]),
            "mkt_beta_quadratic_model": float(m2.params["mkt"]),
            "mkt_sq_coef": float(m2.params["mkt_sq"]),
            "r2_linear": float(m1.rsquared),
            "r2_quadratic": float(m2.rsquared),
        }
        print(" ", col, {k: round(v, 3) for k, v in mk[col].items()})
    res["alpha_controls"] = mk

    print("\n== E. window length sensitivity")
    wl = {}
    for w in [20, 21, 22]:
        dd = vrp.add_payoffs(vrp.load_frame(w)).dropna(subset=["vix"]).dropna(subset=["rv_fwd"])
        wl[w] = {
            "vix_above_realized": float((dd["vrp_volpts"] > 0).mean()),
            "mean_gap_volpts": float(dd["vrp_volpts"].mean()),
            "mean_R_var": float(dd["R_var"].mean()),
            "t_nw_R_var": su.newey_west_t(dd["R_var"], w - 1),
            "mean_R_vol": float(dd["R_vol"].mean()),
            "t_nw_R_vol": su.newey_west_t(dd["R_vol"], w - 1),
        }
        print(" ", w, {k: round(v, 3) for k, v in wl[w].items()})
    res["window_sensitivity"] = wl

    print("\n== F. descriptive: premium by VIX tercile at the window start (all daily windows; overlapping, so no t-stats)")
    d2 = d.copy()
    d2["tercile"] = pd.qcut(d2["vix"], 3, labels=["low", "middle", "high"])
    g = d2.groupby("tercile", observed=True)
    terc = pd.DataFrame(
        {
            "vix_min": g["vix"].min(),
            "vix_max": g["vix"].max(),
            "mean_vix": g["vix"].mean(),
            "mean_realized_vol": g.apply(lambda x: (100 * np.sqrt(x["rv_fwd"])).mean(), include_groups=False),
            "mean_gap_volpts": g["vrp_volpts"].mean(),
            "mean_R_var": g["R_var"].mean(),
            "share_R_var_negative": g["R_var"].apply(lambda x: (x < 0).mean()),
            "worst_R_var": g["R_var"].min(),
        }
    )
    print(terc.round(3).to_string())
    res["vix_tercile_table"] = terc.round(4).to_dict(orient="index")

    print("\n== G. estimator and inference robustness")
    lag_res = {}
    for L in [10, 20, 30, 42, 63]:
        lag_res[L] = {"R_var_t": su.newey_west_t(d["R_var"], L), "R_vol_t": su.newey_west_t(d["R_vol"], L)}
        print(f"  HAC lags {L:2d}: t(R_var) = {lag_res[L]['R_var_t']:.2f}   t(R_vol) = {lag_res[L]['R_vol_t']:.2f}")
    res["hac_lag_sensitivity"] = lag_res

    from arch.data import sp500 as _sp

    ohlc = _sp.load()
    prev_close = ohlc["Close"].shift(1)
    # Parkinson range variance for the trading session plus the squared overnight gap (valid in 2014-2018, where Open != prior Close)
    day_var = (np.log(ohlc["High"] / ohlc["Low"]) ** 2) / (4.0 * np.log(2.0)) + np.log(ohlc["Open"] / prev_close) ** 2
    rv_range = (252.0 / WINDOW) * day_var.rolling(WINDOW).sum().shift(-WINDOW)
    dd = d.copy()
    dd["rv_range"] = rv_range.reindex(dd.index)
    dd = dd.dropna(subset=["rv_range"])
    gap_rng = dd["vix"] - 100.0 * np.sqrt(dd["rv_range"])
    r_rng = 1.0 - dd["rv_range"] / dd["K"]
    corr = float(np.corrcoef(np.sqrt(dd["rv_range"]), np.sqrt(dd["rv_fwd"]))[0, 1])
    rng_res = {
        "mean_gap_volpts_range_based": float(gap_rng.mean()),
        "share_vix_above_range_based": float((gap_rng > 0).mean()),
        "mean_R_var_range_based": float(r_rng.mean()),
        "t_nw_R_var_range_based": su.newey_west_t(r_rng, WINDOW - 1),
        "corr_range_vs_close_to_close_vol": corr,
        "mean_ratio_range_over_close_variance": float((dd["rv_range"] / dd["rv_fwd"]).mean()),
    }
    print("  range-based realized variance (Parkinson + overnight gap) instead of close-to-close:")
    for k, v in rng_res.items():
        print(f"    {k:42s} {v:8.3f}")
    res["range_based_realized_variance"] = rng_res

    with open(os.path.join(OUT, "vrp_robustness.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("\nsaved results/vrp_robustness.json")


if __name__ == "__main__":
    main()
