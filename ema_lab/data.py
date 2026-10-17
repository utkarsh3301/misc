"""
Loaders for the processed datasets built by scripts/fetch_data.py.

Every loader returns a DataFrame with float columns open, high, low,
close, volume on a sorted DatetimeIndex. Cleaning that depends on
judgement (which days to drop, how to treat corporate actions) lives
here rather than in the fetch step, so it is visible and easy to change.
"""

import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")

OHLCV = ["open", "high", "low", "close", "volume"]

# NSE regular session is 09:15-15:30. The 1-minute source stamps bars by
# their end time, so a full session is the 375 bars stamped 09:16..15:30.
SESSION_OPEN_MIN = 9 * 60 + 15
SESSION_BARS = 375

# Corporate actions the overnight gap rule below cannot see because the
# price collapse happened inside the ex-date session (demerger pricing).
CORPORATE_ACTION_OVERRIDES = {
    "adanient": ["2015-06-03"],
}


def _check_dataset(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found. Run: python scripts/fetch_data.py")


# ---------------------------------------------------------------------------
# NSE 1-minute index data
# ---------------------------------------------------------------------------

def load_intraday(symbol, start="2011-01-01", end=None, min_bars=300, max_day_jump=0.25):
    """
    1-minute bars for NIFTY, BANKNIFTY, NIFTY_F1, BANKNIFTY_F1 or INDIAVIX.

    start defaults to 2011, the first full year of the current 09:15-15:30
    session (2007-2010 used 09:55 and then 09:00 opens). Days are dropped
    when they have fewer than min_bars bars (Muhurat sessions, feed gaps)
    or when any bar sits more than max_day_jump away from the surrounding
    week's level, which catches two Bank Nifty days in 2015 where the
    source file switches to a different instrument mid-session. The real
    5 Oct 2012 flash crash (about 15%) passes this filter.
    """
    path = os.path.join(PROCESSED, "intraday_1min", f"{symbol}.parquet")
    _check_dataset(path)
    df = pd.read_parquet(path)
    df = df.loc[start:end] if end else df.loc[start:]

    minute = df.index.hour * 60 + df.index.minute
    df = df[(minute > SESSION_OPEN_MIN) & (minute <= SESSION_OPEN_MIN + SESSION_BARS)]

    day = df.index.normalize()
    day_median = df["close"].groupby(day).median()
    reference = day_median.rolling(7, center=True, min_periods=1).median()
    ref_per_bar = reference.reindex(day).to_numpy()
    deviation = np.abs(np.log(df[["low", "high"]].to_numpy() / ref_per_bar[:, None])).max(axis=1)
    bad_days = pd.Index(day[deviation > max_day_jump]).unique()

    counts = df.groupby(day).size()
    short_days = counts.index[counts < min_bars]
    drop = bad_days.union(short_days)
    return df[~day.isin(drop)].copy()


def resample_session(df, minutes):
    """
    Aggregate 1-minute session bars (stamped by bar end) into k-minute
    bars, also stamped by bar end, without crossing session boundaries.
    """
    if minutes == 1:
        return df.copy()
    session_minute = df.index.hour * 60 + df.index.minute - SESSION_OPEN_MIN  # 1..375
    bucket_end = np.minimum(((session_minute - 1) // minutes + 1) * minutes, SESSION_BARS)
    label = df.index.normalize() + pd.to_timedelta(SESSION_OPEN_MIN + bucket_end, unit="min")
    out = df.groupby(label).agg(open=("open", "first"), high=("high", "max"),
                                low=("low", "min"), close=("close", "last"),
                                volume=("volume", "sum"))
    out.index.name = None
    return out


def daily_from_intraday(df):
    out = df.groupby(df.index.normalize()).agg(open=("open", "first"), high=("high", "max"),
                                               low=("low", "min"), close=("close", "last"),
                                               volume=("volume", "sum"))
    out.index.name = None
    return out


# ---------------------------------------------------------------------------
# NSE end-of-day data
# ---------------------------------------------------------------------------

def adjust_corporate_actions(df, name=None, gap_threshold=0.4):
    """
    Back-adjust prices across unadjusted splits, bonuses and demergers.

    eod2_data adjusts most corporate actions, but a handful slip through
    (ITC 2005, Bharti 2009, Vedanta 2026, ...). They show up as overnight
    gaps above about 33% with a normal session afterwards, which real
    crashes in this universe never do: Yes Bank 2020, Unitech 2008 and
    Idea 2020 all collapsed intraday from a modest open. Every price
    before such a gap is scaled by open/previous close, i.e. the gap is
    treated as entirely mechanical.
    """
    df = df.astype(float)
    prev_close = df["close"].shift(1)
    gap = np.log(df["open"] / prev_close)
    events = list(df.index[gap.abs() > gap_threshold])
    factors = list((df["open"] / prev_close)[gap.abs() > gap_threshold])
    for d in CORPORATE_ACTION_OVERRIDES.get(name, []):
        d = pd.Timestamp(d)
        if d in df.index:
            i = df.index.get_loc(d)
            events.append(d)
            factors.append(df["close"].iloc[i] / df["close"].iloc[i - 1])
    for d, f in sorted(zip(events, factors)):
        before = df.index < d
        df.loc[before, ["open", "high", "low", "close"]] *= f
        df.loc[before, "volume"] /= f
    return df


def load_eod(name, start="2005-01-01", end=None):
    """
    Daily OHLCV from eod2_data, e.g. load_eod("reliance") or
    load_eod("nifty bank"). start defaults to 2005 because eod2 notes
    that NSE adjustment data before 2005 is incomplete.
    """
    key = name.replace(" ", "_")
    path = os.path.join(PROCESSED, "eod_daily", f"{key}.parquet")
    _check_dataset(path)
    df = pd.read_parquet(path)
    is_index = key.startswith("nifty") or key == "india_vix"
    if not is_index:
        df = adjust_corporate_actions(df, name=key)
    return df.loc[start:end] if end else df.loc[start:]


def load_index_daily(symbol):
    """
    Long daily history for NIFTY or BANKNIFTY: daily bars built from the
    1-minute file until eod2 coverage starts (Feb 2012), eod2 after that.
    Over 2,708 overlapping days the two agree to a median 5 bps on close
    and exactly on high/low, with 0.991 daily return correlation.
    """
    eod_name = {"NIFTY": "nifty_50", "BANKNIFTY": "nifty_bank"}[symbol]
    eod = load_eod(eod_name, start="1990-01-01")
    early = daily_from_intraday(load_intraday(symbol, start="2007-01-01", min_bars=200))
    early = early[early.index < eod.index[0]]
    return pd.concat([early, eod])[OHLCV]


# ---------------------------------------------------------------------------
# Multi-asset (OANDA CFDs, Bitstamp BTC)
# ---------------------------------------------------------------------------

MULTI_ASSETS = ["SPX500_USD", "NAS100_USD", "EUR_USD", "GBP_USD", "XAU_USD", "WTICO_USD", "BTC_USD"]


def load_multi(instrument, freq="1d"):
    path = os.path.join(PROCESSED, "multi_asset", f"{instrument}_{freq}.parquet")
    _check_dataset(path)
    df = pd.read_parquet(path)
    df.index.name = None
    return df[OHLCV]
