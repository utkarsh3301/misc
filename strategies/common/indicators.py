"""
Shared technical indicators used across the strategy modules. Plain
pandas/numpy implementations operating on an OHLCV DataFrame with columns
open, high, low, close, volume and a datetime index.
"""

import numpy as np
import pandas as pd


def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def atr(df, period=14):
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def session_vwap(df):
    """VWAP reset at the start of each session. Assumes df covers one session."""
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_pv = (typical * df["volume"]).cumsum()
    cum_vol = df["volume"].cumsum().replace(0, np.nan)
    return cum_pv / cum_vol


def adx(df, period=14):
    high, low = df["high"], df["low"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr_smoothed = atr(df, period=1)  # span=1 ewm reduces to the raw true range
    atr_s = tr_smoothed.ewm(span=period, adjust=False).mean()

    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(span=period, adjust=False).mean() / atr_s
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(span=period, adjust=False).mean() / atr_s
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_line = dx.ewm(span=period, adjust=False).mean()
    return adx_line, plus_di, minus_di


def supertrend(df, period=10, multiplier=3.0):
    hl2 = (df["high"] + df["low"]) / 2.0
    atr_s = atr(df, period)
    upper = (hl2 + multiplier * atr_s).copy()
    lower = (hl2 - multiplier * atr_s).copy()

    trend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    trend.iloc[0] = upper.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(df)):
        close = df["close"].iloc[i]
        if direction.iloc[i - 1] == 1:
            lower.iloc[i] = max(lower.iloc[i], lower.iloc[i - 1])
        else:
            upper.iloc[i] = min(upper.iloc[i], upper.iloc[i - 1])

        if close > upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close < lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        trend.iloc[i] = lower.iloc[i] if direction.iloc[i] == 1 else upper.iloc[i]

    return trend, direction


def bollinger(df, period=20, num_std=2.0):
    mid = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()
    return mid - num_std * std, mid, mid + num_std * std


def keltner(df, period=20, multiplier=1.5):
    mid = df["close"].ewm(span=period, adjust=False).mean()
    rng = atr(df, period)
    return mid - multiplier * rng, mid, mid + multiplier * rng
