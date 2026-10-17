"""
Technical indicators as plain pandas operations on an OHLCV DataFrame.

EMA uses the standard recursive form (adjust=False, alpha = 2/(n+1)),
which is what charting platforms and broker terminals show. ATR, ADX and
RSI use Wilder smoothing (alpha = 1/n), as in Wilder's original
definitions and TradingView's defaults.
"""

import numpy as np
import pandas as pd


def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def sma(series, n):
    return series.rolling(n).mean()


def wilder(series, n):
    return series.ewm(alpha=1.0 / n, adjust=False).mean()


def true_range(df):
    prev_close = df["close"].shift(1)
    return pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)


def atr(df, n=14):
    return wilder(true_range(df), n)


def adx(df, n=14):
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    atr_n = atr(df, n)
    plus_di = 100 * wilder(plus_dm, n) / atr_n
    minus_di = 100 * wilder(minus_dm, n) / atr_n
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return wilder(dx.fillna(0), n), plus_di, minus_di


def rsi(series, n=14):
    delta = series.diff()
    gain = wilder(delta.clip(lower=0), n)
    loss = wilder(-delta.clip(upper=0), n)
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100)


def macd(series, fast=12, slow=26, signal=9):
    line = ema(series, fast) - ema(series, slow)
    sig = ema(line, signal)
    return line, sig, line - sig
