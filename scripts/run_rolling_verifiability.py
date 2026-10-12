"""How often does a window of N years let you "verify" a premium we know exists?

Run from the repo root:
    PYTHONPATH=. python3 scripts/run_rolling_verifiability.py

Real data: Fama-French monthly factors 1926-07 to 2018-11 bundled in the arch
package. For each rolling window length we compute the t-statistic of the mean
return and report how often it clears conventional thresholds. This is an
empirical power estimate for premia with long positive histories.
"""
import json
import os

import numpy as np
import pandas as pd
from arch.data import frenchdata

OUT = "results"
WINDOWS_YEARS = [3, 5, 10, 20, 30]


def load():
    fd = frenchdata.load().copy()
    ints = fd.index.astype("int64")
    fd.index = pd.to_datetime(pd.Series(ints).astype(str).values, format="%Y%m")
    return fd


def main():
    os.makedirs(OUT, exist_ok=True)
    fd = load()
    print("coverage:", fd.index[0].date(), "to", fd.index[-1].date(), "months:", len(fd))
    rows = []
    full = {}
    for col in ["Mkt-RF", "SMB", "HML"]:
        x = fd[col] / 100.0
        n = len(x)
        sr = x.mean() / x.std(ddof=1) * np.sqrt(12)
        t = x.mean() / (x.std(ddof=1) / np.sqrt(n))
        full[col] = {"sharpe_annual": float(sr), "t_full_sample": float(t), "years": n / 12.0}
        print(f"\n{col}: full-sample annual Sharpe {sr:.2f}, t {t:.2f} over {n/12:.0f} years")
        for L in WINDOWS_YEARS:
            w = L * 12
            m = x.rolling(w).mean()
            sd = x.rolling(w).std(ddof=1)
            tt = (m / (sd / np.sqrt(w))).dropna()
            mm = m.dropna()
            rows.append(
                {
                    "series": col,
                    "window_years": L,
                    "n_windows": int(len(tt)),
                    "share_t_above_1.645": float((tt > 1.645).mean()),
                    "share_t_above_1.96": float((tt > 1.96).mean()),
                    "share_t_above_3": float((tt > 3.0).mean()),
                    "share_mean_negative": float((mm < 0).mean()),
                    "median_t": float(tt.median()),
                }
            )
    tab = pd.DataFrame(rows)
    print()
    print(tab.round(3).to_string(index=False))
    tab.round(4).to_csv(os.path.join(OUT, "rolling_premium_verifiability.csv"), index=False)
    with open(os.path.join(OUT, "rolling_premium_verifiability.json"), "w") as f:
        json.dump({"full_sample": full}, f, indent=2)
    print("\nsaved results/rolling_premium_verifiability.csv")


if __name__ == "__main__":
    main()
