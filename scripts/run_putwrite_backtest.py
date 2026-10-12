"""Run the Design A put-writing harness on local CSV files.

STATUS: plumbing is tested on a hand-built fixture only; this script has never been run on market data.

Example (from the repo root), once an SPX chain, settlement levels and a benchmark are available:
    PYTHONPATH=. python3 scripts/run_putwrite_backtest.py --chain chain.csv --format optionsdx \
        --settlement settle.csv --benchmark spxtr.csv --rate 0.02 --fill bid --fee 0.65

settle.csv and spxtr.csv each need a date column (first) and a numeric level column (last).
For AM-settled SPX monthlies the settlement level is the special opening quotation, not the close.
Outputs: results/putwrite_trades.csv and a JSON summary on stdout.
"""
import argparse
import json
import os

import pandas as pd

from src import putwrite as pw


def load_series(path):
    df = pd.read_csv(path)
    first = df.columns[0]
    df[first] = pd.to_datetime(df[first])
    df = df.set_index(first).sort_index()
    return df.select_dtypes("number").iloc[:, -1].dropna()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", required=True)
    ap.add_argument("--format", choices=["normalized", "optionsdx"], default="normalized")
    ap.add_argument("--settlement", required=True)
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--rate", type=float, default=0.0, help="annual cash rate on the collateral, as a decimal")
    ap.add_argument("--target-dte", type=int, default=35)
    ap.add_argument("--target-delta", type=float, default=0.16)
    ap.add_argument("--fill", choices=["bid", "mid"], default="bid")
    ap.add_argument("--fee", type=float, default=0.0, help="all-in fee per contract in dollars")
    ap.add_argument("--out-dir", default="results")
    args = ap.parse_args(argv)

    chain = pw.load_chain(args.chain, fmt=args.format)
    trades = pw.put_write_backtest(
        chain,
        load_series(args.settlement),
        args.rate,
        target_dte=args.target_dte,
        target_delta=args.target_delta,
        fill=args.fill,
        fee_per_contract=args.fee,
    )
    os.makedirs(args.out_dir, exist_ok=True)
    trades.to_csv(os.path.join(args.out_dir, "putwrite_trades.csv"), index=False)
    res = pw.evaluate(trades, load_series(args.benchmark), rf_annual=args.rate)
    print(json.dumps(res, indent=2, default=float))
    return res


if __name__ == "__main__":
    main()
