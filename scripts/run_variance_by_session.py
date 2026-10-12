"""Mechanism check: how S&P 500 variance accrues overnight, intraday and over weekends.

Run from the repo root:
    PYTHONPATH=. python3 scripts/run_variance_by_session.py

This is NOT a profit test. Option prices are not used. It measures the variance
clock that overnight and weekend option-mispricing claims (Muravyev and Ni 2020;
Jones and Shemesh 2018) rely on. Caveat: the SPX index open is computed from the
first prints of constituents and can be stale, which biases the overnight share
down and the intraday share up.
"""
import json
import os

import numpy as np
import pandas as pd
from arch.data import sp500

OUT = "results"


def main():
    os.makedirs(OUT, exist_ok=True)
    d = sp500.load()[["Open", "Close"]].copy()
    d["prev_close"] = d["Close"].shift(1)
    d["gap_days"] = d.index.to_series().diff().dt.days
    d = d.dropna()
    d["overnight"] = np.log(d["Open"] / d["prev_close"])
    d["intraday"] = np.log(d["Close"] / d["Open"])
    d["c2c"] = np.log(d["Close"] / d["prev_close"])

    print("== data check: share of days where Open equals previous Close exactly, by year")
    z = (d["Open"] == d["prev_close"]).groupby(d.index.year).mean()
    print(z.round(3).to_string())
    bad_years = z[z > 0.2].index.tolist()
    print("  years with >20% open==prev close (open unusable for the overnight split):", bad_years)

    ok = d.loc[~d.index.year.isin(bad_years)].copy()
    print(f"  usable sample: {ok.index[0].date()} to {ok.index[-1].date()}, {len(ok)} days")

    res = {"unusable_open_years": [int(y) for y in bad_years], "sample": [str(ok.index[0].date()), str(ok.index[-1].date()), int(len(ok))]}

    print("\n== variance per session (daily log-return squared, in basis points squared)")
    ok["gap_class"] = np.where(ok["gap_days"] == 1, "1d", np.where(ok["gap_days"] == 3, "weekend3d", np.where(ok["gap_days"] == 2, "2d", "4d+")))
    g = ok.groupby("gap_class")
    tab = pd.DataFrame(
        {
            "n": g.size(),
            "gap_days_mean": g["gap_days"].mean(),
            "overnight_var_bp2": g["overnight"].apply(lambda x: float((x ** 2).mean() * 1e8)),
            "intraday_var_bp2": g["intraday"].apply(lambda x: float((x ** 2).mean() * 1e8)),
            "c2c_var_bp2": g["c2c"].apply(lambda x: float((x ** 2).mean() * 1e8)),
        }
    )
    tab["overnight_var_per_cal_day"] = tab["overnight_var_bp2"] / tab["gap_days_mean"]
    print(tab.round(1).to_string())
    res["by_gap_class"] = tab.round(3).to_dict(orient="index")

    intr = float((ok["intraday"] ** 2).mean() * 1e8)
    on1 = float(tab.loc["1d", "overnight_var_bp2"])
    onw = float(tab.loc["weekend3d", "overnight_var_bp2"])
    print(f"\n  intraday variance per trading day: {intr:.1f}")
    print(f"  ordinary overnight (1 calendar day) variance: {on1:.1f}  = {on1/intr:.2f} x intraday")
    print(f"  weekend overnight (3 calendar days) variance: {onw:.1f}  = {onw/on1:.2f} x ordinary overnight (calendar-time clock would say 3.00)")
    total_c2c = float((ok["c2c"] ** 2).mean() * 1e8)
    share_on = float((ok["overnight"] ** 2).mean() * 1e8) / total_c2c
    print(f"  overnight share of close-to-close second moment: {share_on:.3f}")
    res["summary"] = {
        "intraday_var_bp2": intr,
        "overnight_1d_var_bp2": on1,
        "overnight_weekend_var_bp2": onw,
        "weekend_over_ordinary_overnight": onw / on1,
        "overnight_share_of_c2c": share_on,
    }

    print("\n== close-to-close variance by weekday (Monday spans the weekend)")
    wk = ok.groupby(ok.index.dayofweek)["c2c"].apply(lambda x: float((x ** 2).mean() * 1e8))
    wk.index = ["Mon", "Tue", "Wed", "Thu", "Fri"][: len(wk)]
    print(wk.round(1).to_string())
    others = wk.drop("Mon").mean()
    print(f"  Monday / average of Tue-Fri = {wk['Mon']/others:.2f}  (calendar-time clock would say 3.00)")
    res["weekday_c2c_var_bp2"] = wk.round(3).to_dict()
    res["monday_over_other_days"] = float(wk["Mon"] / others)

    print("\n== subperiods")
    sub = {}
    for name, lo, hi in [("first half", ok.index[0], ok.index[len(ok) // 2]), ("second half", ok.index[len(ok) // 2], ok.index[-1])]:
        s = ok.loc[lo:hi]
        gw = s[s["gap_days"] == 3]
        g1 = s[s["gap_days"] == 1]
        sub[name] = {
            "weekend_over_ordinary_overnight": float((gw["overnight"] ** 2).mean() / (g1["overnight"] ** 2).mean()),
            "overnight_share_c2c": float((s["overnight"] ** 2).mean() / (s["c2c"] ** 2).mean()),
        }
        print(" ", name, str(lo.date()), str(hi.date()), {k: round(v, 3) for k, v in sub[name].items()})
    res["subperiods"] = sub

    print("\n== weekend versus ordinary-day close-to-close variance, full 1999-2018 (needs no Open prices)")
    full = d.copy()
    wk_rob = {}
    for name, x in [
        ("1999-2018", full),
        ("ex 2008-2009", full.loc[~full.index.year.isin([2008, 2009])]),
        ("1999-2007", full.loc[:"2007-12-31"]),
        ("2010-2018", full.loc["2010-01-01":]),
    ]:
        wkd = x[x["gap_days"] == 3]
        one = x[x["gap_days"] == 1]
        vr = float((wkd["c2c"] ** 2).mean() / (one["c2c"] ** 2).mean())
        ar = float(wkd["c2c"].abs().mean() / one["c2c"].abs().mean())
        wk_rob[name] = {"n_weekend": int(len(wkd)), "n_ordinary": int(len(one)), "variance_ratio": vr, "mean_abs_return_ratio": ar}
        print(f"  {name:13s} Fri->Mon vs ordinary day: variance ratio {vr:.2f}  mean |return| ratio {ar:.2f}  (calendar clock: 3.00)")
    res["weekend_vs_ordinary_c2c"] = wk_rob

    with open(os.path.join(OUT, "variance_by_session.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("\nsaved results/variance_by_session.json")


if __name__ == "__main__":
    main()
