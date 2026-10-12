"""Real-data variance risk premium study: VIX versus realized S&P 500 variance, 2014-2018.

Run from the repo root:
    PYTHONPATH=. python3 scripts/run_vrp_study.py

Payoffs are for the SHORT side of a 30 day variance swap proxy (strike = VIX^2)
and a volatility swap proxy (strike = VIX). Nothing here is simulated: VIX and
S&P 500 closes are the real series bundled in the arch package.
"""
import json
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src import stats_utils as su
from src import vrp

WINDOW = 21
PPY = 252.0 / WINDOW
PAYOFFS = ["R_var", "R_var_cap", "R_vol"]
OUT = "results"


def hac_ols(y, X, lags=20):
    X = sm.add_constant(X)
    return sm.OLS(y, X, missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def sharpe_fn(y):
    return y.mean() / y.std(ddof=1) * np.sqrt(PPY)


def main():
    os.makedirs(OUT, exist_ok=True)
    res = {}
    df = vrp.add_payoffs(vrp.load_frame(WINDOW)).dropna(subset=["vix"])
    d = df.dropna(subset=["rv_fwd"]).copy()
    d["rv_vol"] = 100.0 * np.sqrt(d["rv_fwd"])
    m0 = vrp.nonoverlap(df, WINDOW, 0).copy()
    m0["rv_vol"] = 100.0 * np.sqrt(m0["rv_fwd"])

    print("== 1. coverage")
    res["coverage"] = {
        "first_window_start": str(d.index[0].date()),
        "last_window_start": str(d.index[-1].date()),
        "daily_windows": int(len(d)),
        "nonoverlap_windows": int(len(m0)),
    }
    print(res["coverage"])

    print("\n== 2. size of the premium (vol points, variance points)")
    k_mean = float((d["K"] * 1e4).mean())
    rv_mean = float((d["rv_fwd"] * 1e4).mean())
    prem = {
        "mean_vix": float(d["vix"].mean()),
        "mean_realized_vol_forward": float(d["rv_vol"].mean()),
        "mean_vrp_volpts": float(d["vrp_volpts"].mean()),
        "share_windows_vix_above_realized": float((d["vrp_volpts"] > 0).mean()),
        "mean_strike_var_pts": k_mean,
        "mean_realized_var_pts": rv_mean,
        "realized_over_strike_var_ratio": rv_mean / k_mean,
    }
    res["premium"] = prem
    for k, v in prem.items():
        print(f"  {k:40s} {v:10.3f}")

    print("\n== 3. payoff statistics, non-overlapping monthly windows, averaged over 21 start offsets")
    rows = []
    for p in PAYOFFS:
        per_offset = []
        for off in range(WINDOW):
            s = vrp.nonoverlap(df, WINDOW, off)[p].dropna()
            st = su.describe(s, PPY)
            per_offset.append(st)
        sh = np.array([x["sharpe_annual"] for x in per_offset])
        tt = np.array([x["t_naive"] for x in per_offset])
        mn = np.array([x["mean"] for x in per_offset])
        rows.append(
            {
                "payoff": p,
                "mean_per_window": mn.mean(),
                "sharpe_mean_over_offsets": sh.mean(),
                "sharpe_min": sh.min(),
                "sharpe_max": sh.max(),
                "t_naive_mean": tt.mean(),
                "n_per_offset": per_offset[0]["n"],
            }
        )
    tab3 = pd.DataFrame(rows).set_index("payoff")
    print(tab3.round(3).to_string())
    res["offset_table"] = tab3.round(4).to_dict(orient="index")

    print("\n== 4. offset-0 sample: full description and HAC t-stat on all overlapping daily windows")
    res["offset0"] = {}
    for p in PAYOFFS:
        st = su.describe(m0[p].dropna(), PPY)
        nw = su.newey_west_t(d[p], lags=WINDOW - 1)
        st["t_newey_west_daily_overlapping"] = nw
        res["offset0"][p] = {k: float(v) for k, v in st.items()}
        print(
            f"  {p:10s} n={st['n']:3d} mean={st['mean']:.3f} sd={st['sd']:.3f} SRann={st['sharpe_annual']:.2f} "
            f"t_naive={st['t_naive']:.2f} t_NW(daily,20lags)={nw:.2f} skew={st['skew']:.2f} "
            f"kurt={st['kurtosis']:.2f} worst={st['worst']:.2f} pos={st['share_positive']:.2f}"
        )

    print("\n== 5. by calendar year of window start (all daily windows)")
    g = d.groupby(d.index.year)
    by_year = pd.DataFrame(
        {
            "n_days": g.size(),
            "mean_vix": g["vix"].mean(),
            "mean_rv_vol": g["rv_vol"].mean(),
            "mean_vrp_volpts": g["vrp_volpts"].mean(),
            "mean_R_var": g["R_var"].mean(),
            "mean_R_var_cap": g["R_var_cap"].mean(),
            "mean_R_vol": g["R_vol"].mean(),
            "share_R_var_neg": g["R_var"].apply(lambda x: (x < 0).mean()),
        }
    )
    print(by_year.round(3).to_string())
    res["by_year"] = by_year.round(4).to_dict(orient="index")

    print("\n== 6. worst non-overlapping windows (offset 0)")
    worst = m0.nsmallest(6, "R_var")[["vix", "rv_vol", "R_var", "R_var_cap", "R_vol", "ret_fwd"]]
    print(worst.round(3).to_string())
    res["worst_offset0"] = {str(i.date()): {c: float(v) for c, v in r.items()} for i, r in worst.iterrows()}
    wd = d.nsmallest(1, "R_var")[["vix", "rv_vol", "R_var", "R_var_cap", "R_vol", "ret_fwd"]]
    print("  worst single daily-start window across all 21 offsets:")
    print(wd.round(3).to_string())
    res["worst_any_offset"] = {str(i.date()): {c: float(v) for c, v in r.items()} for i, r in wd.iterrows()}

    print("\n== 7. fragility: drop the single worst window, and drop Jan-Feb 2018 start dates")
    frag = {}
    for p in PAYOFFS:
        s_all = m0[p].dropna()
        s_drop1 = s_all.drop(s_all.idxmin())
        ev = (d.index >= "2018-01-02") & (d.index <= "2018-02-28")
        s_ex_daily = d.loc[~ev, p]
        mev = (m0.index >= "2018-01-02") & (m0.index <= "2018-02-28")
        s_ex_m0 = m0.loc[~mev, p].dropna()
        frag[p] = {
            "sharpe_all": float(sharpe_fn(s_all)),
            "sharpe_drop_worst_window": float(sharpe_fn(s_drop1)),
            "sharpe_ex_janfeb2018_starts": float(sharpe_fn(s_ex_m0)),
            "t_nw_all_daily": float(su.newey_west_t(d[p], WINDOW - 1)),
            "t_nw_ex_event_daily": float(su.newey_west_t(s_ex_daily, WINDOW - 1)),
        }
        print(" ", p, {k: round(v, 2) for k, v in frag[p].items()})
    res["fragility"] = frag

    print("\n== 8. verifiability math (offset-0 monthly sample)")
    ver = {}
    for p in PAYOFFS:
        s = m0[p].dropna()
        st = su.describe(s, PPY)
        sr_p = st["sharpe_period"]
        se_p = su.sharpe_se(sr_p, st["n"], st["skew"], st["kurtosis"])
        se_ann = se_p * np.sqrt(PPY)
        trl95 = su.min_track_record_periods(sr_p, st["skew"], st["kurtosis"], z=1.645) / PPY
        trl975 = su.min_track_record_periods(sr_p, st["skew"], st["kurtosis"], z=1.96) / PPY
        # same, pretending returns were normal (skew 0, kurtosis 3)
        trl95_normal = su.min_track_record_periods(sr_p, 0.0, 3.0, z=1.645) / PPY
        lo, hi = su.block_bootstrap_ci(s.values, sharpe_fn, block=3, reps=5000, seed=1)
        ver[p] = {
            "sharpe_annual": float(st["sharpe_annual"]),
            "se_annual_mertens": float(se_ann),
            "ci95_block_bootstrap": [float(lo), float(hi)],
            "years_needed_t1645_with_sample_moments": float(trl95),
            "years_needed_t196_with_sample_moments": float(trl975),
            "years_needed_t1645_if_normal": float(trl95_normal),
            "years_in_sample": float(st["n"] / PPY),
        }
        print(
            f"  {p:10s} SR={st['sharpe_annual']:.2f} SE={se_ann:.2f} boot95=[{lo:.2f},{hi:.2f}] "
            f"yrs_needed(95% 1-sided)={trl95:.1f} (normal-returns case {trl95_normal:.1f}) sample={st['n']/PPY:.1f}y"
        )
    res["verifiability"] = ver

    print("\n== 9. deflated Sharpe ratio across the 3 payoff definitions tried")
    srs = []
    for p in PAYOFFS:
        s = m0[p].dropna()
        srs.append(s.mean() / s.std(ddof=1))
    var_sr = float(np.var(srs, ddof=1))
    dsr = {}
    for p in PAYOFFS:
        s = m0[p].dropna()
        st = su.describe(s, PPY)
        dsr[p] = su.deflated_sharpe(st["sharpe_period"], st["n"], st["skew"], st["kurtosis"], len(PAYOFFS), var_sr)
        print(f"  {p:10s} DSR (prob. true Sharpe beats luck benchmark) = {dsr[p]:.3f}")
    res["deflated_sharpe_3_trials"] = dsr

    print("\n== 10. market exposure of the short-variance payoff (offset-0 monthly)")
    mk = {}
    for p in ["R_var", "R_var_cap", "R_vol"]:
        y = m0[p]
        x = m0["ret_fwd"]
        lin = hac_ols(y, x.rename("mkt"), lags=2)
        X2 = pd.concat([x.rename("mkt"), (x ** 2).rename("mkt_sq")], axis=1)
        quad = hac_ols(y, X2, lags=2)
        mk[p] = {
            "beta": float(lin.params["mkt"]),
            "beta_t": float(lin.tvalues["mkt"]),
            "alpha_per_window": float(lin.params["const"]),
            "alpha_t": float(lin.tvalues["const"]),
            "r2_linear": float(lin.rsquared),
            "quad_mkt_sq_coef": float(quad.params["mkt_sq"]),
            "quad_mkt_sq_t": float(quad.tvalues["mkt_sq"]),
            "r2_quadratic": float(quad.rsquared),
        }
        print(" ", p, {k: round(v, 3) for k, v in mk[p].items()})
    res["market_exposure"] = mk

    print("\n== 11. forecasting regressions on all daily windows (HAC 20 lags)")
    mz = hac_ols(d["rv_fwd"], d[["K"]])
    mz2 = hac_ols(d["rv_fwd"], d[["K", "rv_trail"]])
    fc = {
        "mincer_zarnowitz_slope_on_K": float(mz.params["K"]),
        "mincer_zarnowitz_slope_t_vs_zero": float(mz.tvalues["K"]),
        "mincer_zarnowitz_slope_t_vs_one": float((mz.params["K"] - 1.0) / mz.bse["K"]),
        "mincer_zarnowitz_const": float(mz.params["const"]),
        "mincer_zarnowitz_r2": float(mz.rsquared),
        "joint_slope_K": float(mz2.params["K"]),
        "joint_slope_rv_trail": float(mz2.params["rv_trail"]),
        "joint_r2": float(mz2.rsquared),
    }
    ret_on_vrp = hac_ols(d["ret_fwd"], d[["vrp_exante"]])
    fc["ret_on_exante_vrp_coef"] = float(ret_on_vrp.params["vrp_exante"])
    fc["ret_on_exante_vrp_t"] = float(ret_on_vrp.tvalues["vrp_exante"])
    fc["ret_on_exante_vrp_r2"] = float(ret_on_vrp.rsquared)
    for k, v in fc.items():
        print(f"  {k:40s} {v:10.4f}")
    res["forecasting"] = fc

    with open(os.path.join(OUT, "vrp_summary.json"), "w") as f:
        json.dump(res, f, indent=2)
    m0[["spx", "vix", "rv_vol", "ret_fwd", "R_var", "R_var_cap", "R_vol", "vrp_volpts"]].round(5).to_csv(
        os.path.join(OUT, "vrp_monthly_offset0.csv")
    )
    print("\nsaved results/vrp_summary.json and results/vrp_monthly_offset0.csv")


if __name__ == "__main__":
    main()
