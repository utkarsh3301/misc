"""Power analysis: how long a record can verify a given true Sharpe ratio?

Run from the repo root:
    PYTHONPATH=. python3 scripts/run_power_analysis.py

HYPOTHETICAL. Nothing here is a performance claim. It answers: if a strategy
really had annual Sharpe S, how often would T years of monthly data show a
t-statistic above 1.645 (one-sided 5%)? Two return shapes are compared:
normal returns, and the empirical shape of the real short-variance payoff
(skew about -3.4, kurtosis about 16) taken from the 2014-2018 data.
"""
import json
import os

import numpy as np
import pandas as pd

from src import stats_utils as su
from src import vrp

OUT = "results"
RNG = np.random.default_rng(7)
SHARPES = [0.25, 0.5, 0.75, 1.0, 1.5]
YEARS = [3, 5, 10, 20, 30]


def main():
    os.makedirs(OUT, exist_ok=True)
    df = vrp.add_payoffs(vrp.load_frame(21)).dropna(subset=["vix"])
    shape = vrp.nonoverlap(df, 21, 0)["R_var"].dropna().values
    st = su.describe(shape, 12)
    skew, kurt = st["skew"], st["kurtosis"]
    print(f"empirical shape: n={st['n']} skew={skew:.2f} kurtosis={kurt:.1f}")

    print("\n== years of data for the sample Sharpe to clear t=1.645 if the sample equals the truth (50% power), and for 80% power (analytic, Mertens variance)")
    rows = []
    for s in SHARPES:
        sr_p = s / np.sqrt(12)
        rows.append(
            {
                "true_sharpe": s,
                "years_50pct_normal": su.min_track_record_periods(sr_p, 0.0, 3.0, z=1.645) / 12,
                "years_80pct_normal": su.min_track_record_periods(sr_p, 0.0, 3.0, z=1.645 + 0.842) / 12,
                "years_50pct_shortvol_shape": su.min_track_record_periods(sr_p, skew, kurt, z=1.645) / 12,
                "years_80pct_shortvol_shape": su.min_track_record_periods(sr_p, skew, kurt, z=1.645 + 0.842) / 12,
            }
        )
    t1 = pd.DataFrame(rows).set_index("true_sharpe")
    print(t1.round(1).to_string())

    print("\n== probability that T years of monthly data show t > 1.645 (hypothetical true Sharpe)")
    print("   the true_sharpe = 0 row is the false-positive rate: how often a strategy with NO edge looks verified")
    out = {"analytic_years": t1.round(2).to_dict(orient="index"), "power": {}}
    for kind in ["normal", "empirical_shape"]:
        grid = {}
        for s in [0.0] + SHARPES:
            grid[s] = {}
            for y in YEARS:
                p = su.power_normal(s, y) if kind == "normal" else su.power_empirical_shape(shape, s, y, RNG)
                grid[s][y] = p
        tab = pd.DataFrame(grid).T
        tab.index.name = "true_sharpe"
        print(f"\n[{kind}]  columns = years of data")
        print(tab.round(2).to_string())
        out["power"][kind] = {str(s): {str(y): round(v, 4) for y, v in row.items()} for s, row in grid.items()}

    with open(os.path.join(OUT, "power_analysis.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nsaved results/power_analysis.json")


if __name__ == "__main__":
    main()
