"""Pre-specified conditional rules for selling variance, with a strict split and trial counting.

Run from the repo root:
    PYTHONPATH=. python3 scripts/run_conditional_rules.py

The six rules below were written down before any result was looked at and are
not tuned. Each decides, using only information known at the start of a
21 trading day window, whether and how much variance to sell. Payoffs are the
real-data short-variance payoff per unit strike variance from src/vrp.py.

Sample: 2015-01 onward (a trailing 252 day history is needed by two rules), split
into in-sample through 2016-12 and out-of-sample from 2017-01. With roughly 24
monthly points per side this is a demonstration of how little such a sample can
tell apart, not a search for a better rule.

Sharpe ratios depend on which trading day the monthly grid starts on (a 47 month
sample has 21 possible non-overlapping grids). The deflated Sharpe ratio is
therefore computed from the Sharpe averaged over all 21 grids, and the single
grid (offset 0) numbers are shown only for comparison.
"""
import json
import os

import numpy as np
import pandas as pd

from src import stats_utils as su
from src import vrp

WINDOW = 21
PPY = 252.0 / WINDOW
SPLIT = "2016-12-31"
OUT = "results"


def sharpe(x):
    x = np.asarray(x, dtype=float)
    return float(x.mean() / x.std(ddof=1) * np.sqrt(PPY)) if x.std(ddof=1) > 0 else float("nan")


def build_weights(df):
    """Rule weights known at the start of each window. Returns (frame with helper columns, weights dict)."""
    df = df.copy()
    df["vix_med252"] = df["vix"].rolling(252).median()
    df["rv_trail_med252"] = df["rv_trail"].rolling(252).median()
    df["prev_R_var"] = df["R_var"].shift(WINDOW)
    w = {
        "R0_always_sell": pd.Series(1.0, index=df.index),
        "R1_vix_above_1y_median": (df["vix"] > df["vix_med252"]).astype(float),
        "R2_exante_vrp_positive": (df["vrp_exante"] > 0).astype(float),
        "R3_vix_below_20": (df["vix"] < 20).astype(float),
        "R4_vol_managed_cap2": (df["rv_trail_med252"] / df["rv_trail"]).clip(0.0, 2.0),
        "R5_skip_after_loss_below_minus1": (df["prev_R_var"].fillna(0.0) > -1.0).astype(float),
    }
    return df, w


def main():
    os.makedirs(OUT, exist_ok=True)
    df = vrp.add_payoffs(vrp.load_frame(WINDOW)).dropna(subset=["vix"])
    df, w = build_weights(df)
    start = df["vix_med252"].first_valid_index()
    d = df.loc[start:].copy()
    for k in w:
        w[k] = w[k].loc[start:]
    ret = {k: (w[k] * d["R_var"]) for k in w}

    n_trials = len(w)
    print(f"sample start {start.date()} ; rules (trials) = {n_trials}")
    rows = []
    sr_avg_period = {}
    for k in w:
        per_off_ann = []
        per_off_period = []
        for off in range(WINDOW):
            s = ret[k].dropna().iloc[off::WINDOW]
            per_off_ann.append(sharpe(s))
            per_off_period.append(s.mean() / s.std(ddof=1))
        sr_avg_period[k] = float(np.mean(per_off_period))
        s0 = ret[k].dropna().iloc[0::WINDOW]
        s_is = s0.loc[:SPLIT]
        s_oos = s0.loc[s0.index > pd.Timestamp(SPLIT)]
        st = su.describe(s0, PPY)
        rows.append(
            {
                "rule": k,
                "share_invested": float((w[k].loc[s0.index] > 0).mean()),
                "months": int(len(s0)),
                "mean_per_month": float(s0.mean()),
                "sharpe_offset0": sharpe(s0),
                "sharpe_avg_21_grids": float(np.nanmean(per_off_ann)),
                "sharpe_grid_min": float(np.nanmin(per_off_ann)),
                "sharpe_grid_max": float(np.nanmax(per_off_ann)),
                "sharpe_in_sample_offset0": sharpe(s_is),
                "sharpe_out_of_sample_offset0": sharpe(s_oos),
                "worst_month": float(s0.min()),
                "skew": float(st["skew"]),
            }
        )
    tab = pd.DataFrame(rows).set_index("rule")
    print(tab.round(2).to_string())

    var_sr = float(np.var(list(sr_avg_period.values()), ddof=1))
    print(f"\nvariance of grid-averaged monthly Sharpe across the {n_trials} trials: {var_sr:.5f}; expected best-of-{n_trials} luck Sharpe (monthly) = {su.expected_max_sharpe(n_trials, var_sr):.3f}")
    dsr = {}
    dsr_offset0 = {}
    sr0_all = [ret[k].dropna().iloc[0::WINDOW] for k in w]
    var_sr0 = float(np.var([s.mean() / s.std(ddof=1) for s in sr0_all], ddof=1))
    for k, s0 in zip(w, sr0_all):
        st = su.describe(s0, PPY)
        dsr[k] = su.deflated_sharpe(sr_avg_period[k], st["n"], st["skew"], st["kurtosis"], n_trials, var_sr)
        dsr_offset0[k] = su.deflated_sharpe(st["sharpe_period"], st["n"], st["skew"], st["kurtosis"], n_trials, var_sr0)
    print("deflated Sharpe ratio (probability the true Sharpe beats the best-of-trials luck level):")
    print(f"  {'rule':34s} {'grid-avg':>9s} {'offset0':>9s}")
    for k in w:
        print(f"  {k:34s} {dsr[k]:9.3f} {dsr_offset0[k]:9.3f}")

    best_is = tab["sharpe_in_sample_offset0"].idxmax()
    print(f"\nbest in-sample rule (offset 0): {best_is}")
    print(f"  its out-of-sample Sharpe: {tab.loc[best_is, 'sharpe_out_of_sample_offset0']:.2f}  | always-sell out-of-sample Sharpe: {tab.loc['R0_always_sell', 'sharpe_out_of_sample_offset0']:.2f}")
    print(f"  its in-sample Sharpe was {tab.loc[best_is, 'sharpe_in_sample_offset0']:.2f}; grid-average full-sample Sharpe {tab.loc[best_is, 'sharpe_avg_21_grids']:.2f} vs always-sell {tab.loc['R0_always_sell', 'sharpe_avg_21_grids']:.2f}")
    best_oos = tab["sharpe_out_of_sample_offset0"].idxmax()
    print(f"best out-of-sample rule (hindsight, not a valid selection): {best_oos} ({tab.loc[best_oos, 'sharpe_out_of_sample_offset0']:.2f})")

    out = {
        "n_trials": n_trials,
        "table": tab.round(4).to_dict(orient="index"),
        "deflated_sharpe_grid_average": dsr,
        "deflated_sharpe_offset0": dsr_offset0,
        "best_in_sample_rule": best_is,
        "best_in_sample_rule_oos_sharpe": float(tab.loc[best_is, "sharpe_out_of_sample_offset0"]),
        "baseline_oos_sharpe": float(tab.loc["R0_always_sell", "sharpe_out_of_sample_offset0"]),
        "sample_start": str(start.date()),
        "split": SPLIT,
    }
    with open(os.path.join(OUT, "conditional_rules.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nsaved results/conditional_rules.json")


if __name__ == "__main__":
    main()
