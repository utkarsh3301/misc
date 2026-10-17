"""
Downloads the public historical datasets used by this branch and
converts them into compact parquet files under data/processed/.

Sources (all public GitHub repositories, read anonymously):

1. aeron7/nifty-banknifty-intraday-data
   1-minute bars for NIFTY and BANKNIFTY spot, their near-month futures
   (NIFTY_F1, BANKNIFTY_F1) and INDIAVIX, 2007/2010 to Feb 2023.
   The full repository is about 22 GB, so this script uses a partial,
   sparse clone that only downloads the five series it needs.
2. BennyThadikaran/eod2_data
   NSE end-of-day OHLCV for stocks and indices, adjusted for splits and
   bonuses, sourced from NSE daily reports and updated weekly.
3. FutureSharks/financial-data
   Assorted multi-asset history (US indices, FX, commodities, crypto).

Usage:
    python scripts/fetch_data.py                 # everything
    python scripts/fetch_data.py intraday        # just one source
    python scripts/fetch_data.py intraday --src /path/to/existing/clone
"""

import argparse
import glob
import os
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
OUT_DIR = os.path.join(ROOT, "data", "processed")

INTRADAY_REPO = "https://github.com/aeron7/nifty-banknifty-intraday-data"
INTRADAY_SYMBOLS = ["NIFTY", "BANKNIFTY", "NIFTY_F1", "BANKNIFTY_F1", "INDIAVIX"]

EOD_REPO = "https://github.com/BennyThadikaran/eod2_data"
EOD_INDICES = [
    "nifty 50", "nifty bank", "nifty 500", "nifty midcap 100", "nifty it",
    "nifty pharma", "nifty fmcg", "nifty metal", "nifty auto", "nifty realty",
    "nifty energy", "nifty financial services", "india vix",
]
# Current and recent Nifty 50 members with long histories, plus former
# members that fell out of the index (yesbank, idea, rcom, unitech, ...).
# The second group is there to blunt survivorship bias: a universe made
# only of today's winners flatters any long-biased trend rule.
EOD_STOCKS = [
    "reliance", "hdfcbank", "icicibank", "infy", "tcs", "sbin", "itc", "lt",
    "kotakbank", "axisbank", "bhartiartl", "hindunilvr", "bajfinance", "maruti",
    "sunpharma", "titan", "ultracemco", "asianpaint", "nestleind", "wipro",
    "hcltech", "techm", "ntpc", "powergrid", "ongc", "coalindia", "tatasteel",
    "jswsteel", "hindalco", "grasim", "cipla", "drreddy", "eichermot",
    "heromotoco", "bajaj-auto", "m&m", "adaniports", "adanient", "britannia",
    "divislab", "apollohosp", "indusindbk", "sbilife", "hdfclife", "bajajfinsv",
    "shreecem", "trent", "bel", "tatapower",
]
EOD_FORMER = [
    "upl", "bpcl", "ioc", "gail", "vedl", "yesbank", "idea", "zeel", "dlf",
    "suzlon", "jpassociat", "unitech", "rcom",
]

MULTI_REPO = "https://github.com/FutureSharks/financial-data"
OANDA_INSTRUMENTS = ["SPX500_USD", "NAS100_USD", "EUR_USD", "GBP_USD", "XAU_USD", "WTICO_USD"]


def sparse_clone(url, dest, patterns):
    """
    Partial clone that only fetches blobs matching the given patterns.
    Safe to call again on an existing clone: the pattern set is replaced
    and any missing blobs are fetched.
    """
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1")
    if not os.path.isdir(os.path.join(dest, ".git")):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--no-checkout",
                        url, dest], check=True, env=env)
    subprocess.run(["git", "-C", dest, "sparse-checkout", "set", "--no-cone", *patterns],
                   check=True, env=env)
    subprocess.run(["git", "-C", dest, "checkout"], check=True, env=env)


# ---------------------------------------------------------------------------
# 1. NIFTY / BANKNIFTY 1-minute bars
# ---------------------------------------------------------------------------

def _read_minute_file(path):
    """
    Rows look like SYMBOL,YYYYMMDD,HH:MM[:SS],O,H,L,C[,V[,OI]]. The column
    count varies by year, so read loosely and keep what is present.
    """
    df = pd.read_csv(path, header=None, dtype=str, on_bad_lines="skip",
                     names=list(range(9)), engine="c")
    df = df.dropna(subset=[1, 2, 3, 4, 5, 6])
    if df.empty:
        return None
    stamp = df[1].str.strip() + df[2].str.strip().str.slice(0, 5)
    idx = pd.to_datetime(stamp, format="%Y%m%d%H:%M", errors="coerce")
    out = pd.DataFrame({
        "open": pd.to_numeric(df[3], errors="coerce"),
        "high": pd.to_numeric(df[4], errors="coerce"),
        "low": pd.to_numeric(df[5], errors="coerce"),
        "close": pd.to_numeric(df[6], errors="coerce"),
        "volume": pd.to_numeric(df[7], errors="coerce") if 7 in df else np.nan,
    })
    out.index = idx
    return out[out.index.notna()]


def clean_ohlc(df):
    """Drop bad rows and force high/low to bracket open/close."""
    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df[(df[["open", "high", "low", "close"]] > 0).all(axis=1)]
    df = df[~df.index.duplicated(keep="last")].sort_index()
    body_hi = df[["open", "close"]].max(axis=1)
    body_lo = df[["open", "close"]].min(axis=1)
    df = df.assign(high=np.maximum(df["high"], body_hi), low=np.minimum(df["low"], body_lo))
    return df


def build_intraday(src):
    if src is None:
        src = os.path.join(RAW_DIR, "nifty-banknifty-intraday-data")
        patterns = [f"**/{s}.txt" for s in INTRADAY_SYMBOLS] + ["Upto_2011/NIFTY_Spot_2007/*"]
        sparse_clone(INTRADAY_REPO, src, patterns)

    files = {s: [] for s in INTRADAY_SYMBOLS}
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d != ".git" and "OPT" not in d.upper()]
        for name in filenames:
            stem = name[:-4] if name.endswith(".txt") else None
            if stem in files:
                files[stem].append(os.path.join(dirpath, name))
            elif os.path.basename(dirpath) == "NIFTY_Spot_2007" and name.endswith(".txt"):
                files["NIFTY"].append(os.path.join(dirpath, name))

    out_dir = os.path.join(OUT_DIR, "intraday_1min")
    os.makedirs(out_dir, exist_ok=True)
    for sym, paths in files.items():
        frames = [f for f in (_read_minute_file(p) for p in sorted(paths)) if f is not None]
        if not frames:
            print(f"[intraday] {sym}: no files found")
            continue
        df = clean_ohlc(pd.concat(frames))
        # Drop the 09:08 pre-open auction print and anything outside the
        # regular session. Timestamps are bar end times (first bar 09:16).
        t = df.index.hour * 100 + df.index.minute
        df = df[(t >= 901) & (t <= 1530)]
        path = os.path.join(out_dir, f"{sym}.parquet")
        df.to_parquet(path)
        days = df.index.normalize().nunique()
        print(f"[intraday] {sym}: {len(paths)} files -> {len(df):,} bars, {days:,} days, "
              f"{df.index.min()} .. {df.index.max()}")


# ---------------------------------------------------------------------------
# 2. NSE end-of-day stocks and indices
# ---------------------------------------------------------------------------

def build_eod(src):
    names = EOD_INDICES + EOD_STOCKS + EOD_FORMER
    if src is None:
        src = os.path.join(RAW_DIR, "eod2_data")
        sparse_clone(EOD_REPO, src, [f"/daily/{n}.csv" for n in names])

    out_dir = os.path.join(OUT_DIR, "eod_daily")
    os.makedirs(out_dir, exist_ok=True)
    for name in names:
        path = os.path.join(src, "daily", f"{name}.csv")
        if not os.path.exists(path):
            print(f"[eod] {name}: missing")
            continue
        df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
        df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
        df = clean_ohlc(df)
        df.to_parquet(os.path.join(out_dir, f"{name.replace(' ', '_')}.parquet"))
    print(f"[eod] {len(names)} daily series -> {out_dir}")


# ---------------------------------------------------------------------------
# 3. Multi-asset: OANDA CFDs (2005 to May 2020) and Bitstamp BTC/USD
# ---------------------------------------------------------------------------

def _resample(df, rule, day_index=None):
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    if day_index is not None:
        out = df.groupby(day_index).agg(agg)
    else:
        out = df.resample(rule).agg(agg)
    return out.dropna(subset=["open"])


def build_multi_asset(src):
    if src is None:
        src = os.path.join(RAW_DIR, "financial-data")
        base = "/pyfinancialdata/data"
        patterns = [f"{base}/currencies/oanda/{i}/" for i in OANDA_INSTRUMENTS]
        patterns.append(f"{base}/cryptocurrencies/bitstamp/BTC_USD/")
        sparse_clone(MULTI_REPO, src, patterns)
    base = os.path.join(src, "pyfinancialdata", "data")

    out_dir = os.path.join(OUT_DIR, "multi_asset")
    os.makedirs(out_dir, exist_ok=True)

    for inst in OANDA_INSTRUMENTS:
        files = sorted(glob.glob(os.path.join(base, "currencies", "oanda", inst, "*", "*.csv")))
        df = pd.concat(pd.read_csv(f, parse_dates=["time"], index_col="time") for f in files)
        df = clean_ohlc(df[["open", "high", "low", "close", "volume"]])
        # OANDA stamps candles by start time in UTC. Daily bars use the
        # usual 17:00 New York rollover, so Sunday evening trades belong
        # to Monday's bar.
        ny = df.index.tz_localize("UTC").tz_convert("America/New_York")
        trade_day = (ny + pd.Timedelta(hours=7)).tz_localize(None).normalize()
        daily = _resample(df, None, day_index=trade_day)
        counts = df.groupby(trade_day).size()
        daily = daily[(daily.index.dayofweek < 5) & (counts.reindex(daily.index) >= 60)]
        hourly = _resample(df, "1h")
        daily.to_parquet(os.path.join(out_dir, f"{inst}_1d.parquet"))
        hourly.to_parquet(os.path.join(out_dir, f"{inst}_1h.parquet"))
        print(f"[multi] {inst}: {len(df):,} 1-min bars -> {len(daily):,} days, "
              f"{df.index.min():%Y-%m-%d} .. {df.index.max():%Y-%m-%d}")

    files = sorted(glob.glob(os.path.join(base, "cryptocurrencies", "bitstamp", "BTC_USD", "*.csv")))
    df = pd.concat(pd.read_csv(f, parse_dates=["date"], index_col="date") for f in files)
    df["volume"] = np.nan
    df = clean_ohlc(df[["open", "high", "low", "close", "volume"]])
    # 2018.csv only holds the first week of January, so stop at 2017.
    df = df[df.index < "2018-01-01"]
    _resample(df, "1D").to_parquet(os.path.join(out_dir, "BTC_USD_1d.parquet"))
    _resample(df, "1h").to_parquet(os.path.join(out_dir, "BTC_USD_1h.parquet"))
    print(f"[multi] BTC_USD: {len(df):,} 1-min bars, {df.index.min():%Y-%m-%d} .. {df.index.max():%Y-%m-%d}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", default="all",
                        choices=["all", "intraday", "eod", "multi"])
    parser.add_argument("--src", default=None,
                        help="use an existing clone instead of downloading")
    args = parser.parse_args()
    if args.source in ("all", "intraday"):
        build_intraday(args.src)
    if args.source in ("all", "eod"):
        build_eod(args.src)
    if args.source in ("all", "multi"):
        build_multi_asset(args.src)


if __name__ == "__main__":
    sys.exit(main())
