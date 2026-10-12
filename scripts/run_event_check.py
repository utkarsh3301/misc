"""Cross-check named volatility events against the bundled VIX and S&P 500 data.

Run from the repo root:
    PYTHONPATH=. python3 scripts/run_event_check.py

Purpose: several literature summaries quote VIX levels for the Aug 2015 and Feb 2018
shocks. This script prints what the bundled data say so that differences between a
secondary source and the data are visible instead of silently trusted.
"""
import json
import os

import numpy as np
import pandas as pd
from arch.data import sp500, vix

OUT = "results"


def main():
    os.makedirs(OUT, exist_ok=True)
    spx = sp500.load()["Close"].rename("spx")
    vx = vix.load()["vix"].rename("vix")
    d = pd.concat([spx, vx], axis=1, join="inner").dropna()
    d["spx_ret"] = d["spx"].pct_change()
    d["vix_chg_pct"] = d["vix"].pct_change()
    res = {}

    print("== data sanity")
    print(f"  rows {len(d)} ; {d.index[0].date()} to {d.index[-1].date()}")
    print(f"  VIX min {d['vix'].min():.2f} on {d['vix'].idxmin().date()} ; max {d['vix'].max():.2f} on {d['vix'].idxmax().date()}")
    gaps = d.index.to_series().diff().dt.days
    print(f"  largest calendar gap between consecutive rows: {int(gaps.max())} days on {gaps.idxmax().date()}")
    res["sanity"] = {
        "rows": int(len(d)),
        "vix_min": float(d["vix"].min()),
        "vix_max": float(d["vix"].max()),
        "vix_max_date": str(d["vix"].idxmax().date()),
    }

    print("\n== ten largest one-day VIX increases")
    top = d.nlargest(10, "vix_chg_pct")[["vix", "vix_chg_pct", "spx_ret"]]
    print(top.round(3).to_string())
    res["largest_vix_jumps"] = {str(i.date()): {c: float(v) for c, v in r.items()} for i, r in top.iterrows()}

    for name, lo, hi in [("Aug 2015", "2015-08-17", "2015-09-02"), ("Feb 2018", "2018-01-26", "2018-02-16")]:
        print(f"\n== {name}")
        w = d.loc[lo:hi, ["spx", "vix", "spx_ret", "vix_chg_pct"]]
        print(w.round(3).to_string())
        res[name] = {str(i.date()): {c: float(v) for c, v in r.items()} for i, r in w.iterrows()}

    j = d.loc["2018-02-05"]
    prev = d.loc[:"2018-02-04"].iloc[-1]
    print(
        f"\nFeb 5 2018 in the bundled data: VIX {prev['vix']:.2f} -> {j['vix']:.2f} ({j['vix'] / prev['vix'] - 1:+.1%}); S&P 500 {j['spx_ret']:+.2%}"
    )
    print("A literature summary quoted 17.16 -> 37.32 (+117%); differences, if any, are due to the source or the data vintage.")
    res["feb5_2018"] = {"prev_vix": float(prev["vix"]), "vix": float(j["vix"]), "change": float(j["vix"] / prev["vix"] - 1.0), "spx_ret": float(j["spx_ret"])}

    with open(os.path.join(OUT, "event_check.json"), "w") as f:
        json.dump(res, f, indent=2)
    print("\nsaved results/event_check.json")


if __name__ == "__main__":
    main()
