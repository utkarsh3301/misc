"""Run the strategy-versus-benchmark verification battery on two local CSV files of index LEVELS.

Usage (from the repo root), for example once Cboe PUT and an S&P 500 total return series are available:
    PYTHONPATH=. python3 scripts/run_index_compare.py --strategy data/PUT.csv --benchmark data/SPXTR.csv \
        --freq monthly --rf 0.03

Each CSV needs a date column (first column) and one numeric level column (the last numeric column is used).
NOTE: in the study environment this script was exercised only on bundled equity series (see tests), never on
an option-strategy index, because the hosts that publish those indexes were blocked by the egress policy.
"""
import argparse
import json

import pandas as pd

from src import index_compare as ic


def load_levels(path):
    df = pd.read_csv(path)
    first = df.columns[0]
    df[first] = pd.to_datetime(df[first])
    df = df.set_index(first).sort_index()
    num = df.select_dtypes("number")
    return num.iloc[:, -1].dropna()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--freq", choices=["daily", "monthly"], default="monthly")
    ap.add_argument("--rf", type=float, default=0.0, help="annual risk-free rate as a decimal")
    args = ap.parse_args()
    s, b = load_levels(args.strategy), load_levels(args.benchmark)
    if args.freq == "monthly":
        s, b = s.resample("ME").last(), b.resample("ME").last()
        ppy, lags = 12, 3
    else:
        ppy, lags = 252, 10
    res = ic.compare(s.pct_change().dropna(), b.pct_change().dropna(), rf_annual=args.rf, periods_per_year=ppy, hac_lags=lags)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
