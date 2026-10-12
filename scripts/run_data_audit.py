"""Data audit of the bundled series: alignment, outliers and cross-source consistency.

Run from the repo root:
    PYTHONPATH=. python3 scripts/run_data_audit.py

Checks that the real series used in the study are internally consistent and aligned with each
other. None of this proves the vendor data are right, but a one-day misalignment between the VIX
and the S&P 500, or a mis-parsed factor date, would show up here.
"""
import json
import os

import numpy as np
import pandas as pd
from arch.data import frenchdata, sp500, vix

OUT = "results"


def audit():
    res = {}
    spx = sp500.load()["Close"]
    vx = vix.load()["vix"].dropna()
    r = np.log(spx).diff().dropna()

    # 1. S&P 500 integrity
    rows_by_year = spx.groupby(spx.index.year).size()
    gaps = spx.index.to_series().diff().dt.days.dropna()
    res["spx"] = {
        "rows": int(len(spx)),
        "duplicate_dates": int(spx.index.duplicated().sum()),
        "non_positive": int((spx <= 0).sum()),
        "rows_per_year_min_max": [int(rows_by_year.min()), int(rows_by_year.max())],
        "largest_calendar_gaps": {str(i.date()): int(v) for i, v in gaps.nlargest(3).items()},
        "worst_days": {str(i.date()): float(v) for i, v in (np.exp(r) - 1).nsmallest(3).items()},
        "best_days": {str(i.date()): float(v) for i, v in (np.exp(r) - 1).nlargest(3).items()},
    }

    # 2. VIX integrity
    res["vix"] = {
        "rows": int(len(vx)),
        "duplicate_dates": int(vx.index.duplicated().sum()),
        "min": float(vx.min()),
        "max": float(vx.max()),
        "non_positive": int((vx <= 0).sum()),
        "dates_not_in_spx": int((~vx.index.isin(spx.index)).sum()),
    }

    # 3. VIX-S&P 500 alignment: the leverage effect should peak at lag 0 and be strongly negative
    dv = np.log(vx).diff().dropna()
    j = pd.concat([dv.rename("dv"), r.rename("r")], axis=1, join="inner").dropna()
    lag_corr = {}
    for lag in (-2, -1, 0, 1, 2):
        lag_corr[lag] = float(j["dv"].corr(j["r"].shift(lag)))
    res["vix_spx_alignment"] = {"corr_dlogvix_vs_spx_return_by_lag": lag_corr}

    # 4. Fama-French date parsing and consistency with the S&P 500 monthly price return
    fd = frenchdata.load().copy()
    ints = fd.index.astype("int64")
    fd.index = pd.to_datetime(pd.Series(ints).astype(str).values, format="%Y%m").to_period("M")
    mkt_total = (fd["Mkt-RF"] + fd["RF"]) / 100.0
    spx_m = spx.resample("ME").last().pct_change().dropna()
    spx_m.index = spx_m.index.to_period("M")
    jm = pd.concat([mkt_total.rename("ff"), spx_m.rename("spx")], axis=1, join="inner").dropna()
    res["french_vs_spx_monthly"] = {
        "months": int(len(jm)),
        "first": str(jm.index[0]),
        "last": str(jm.index[-1]),
        "correlation": float(jm["ff"].corr(jm["spx"])),
        "mean_abs_difference": float((jm["ff"] - jm["spx"]).abs().mean()),
    }
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    res = audit()
    print("== S&P 500")
    for k, v in res["spx"].items():
        print(f"  {k:28s} {v}")
    print("== VIX")
    for k, v in res["vix"].items():
        print(f"  {k:28s} {v}")
    print("== VIX versus S&P 500 alignment (correlation of daily log VIX change with S&P 500 return shifted by lag)")
    for lag, c in res["vix_spx_alignment"]["corr_dlogvix_vs_spx_return_by_lag"].items():
        print(f"  lag {lag:+d}: {c:+.3f}")
    print("== Fama-French market versus S&P 500 monthly price return")
    for k, v in res["french_vs_spx_monthly"].items():
        print(f"  {k:28s} {v}")
    with open(os.path.join(OUT, "data_audit.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("saved results/data_audit.json")


if __name__ == "__main__":
    main()
