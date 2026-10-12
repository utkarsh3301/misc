"""Variance risk premium on real data: VIX squared versus subsequent realized S&P 500 variance.

Data (bundled in the arch package, no network needed):
  S&P 500 daily closes 1999-01-04 to 2018-12-31
  VIX daily closes 2014-01-03 to 2019-01-03

The VIX is the model-free 30 day implied volatility computed by Cboe from SPX
option prices, so (VIX/100)^2 is the standard proxy for the strike of a 30 day
variance swap. Realized variance is the annualized sum of squared daily log
returns over the following 21 trading days.
"""
import numpy as np
import pandas as pd
from arch.data import sp500, vix

TRADING_DAYS = 252
# Variance swaps are normally capped at (2.5 x strike volatility)^2 of realized variance.
CAP_VARIANCE_MULT = 6.25


def load_frame(window=21, end=None):
    """Aligned S&P 500, VIX and forward/trailing realized variance.

    `end` truncates the raw series, which lets tests prove that signals built on
    this frame do not use information after the date they are evaluated.
    """
    spx = sp500.load()["Close"].rename("spx")
    vx = vix.load()["vix"].rename("vix")
    if end is not None:
        spx = spx.loc[:end]
        vx = vx.loc[:end]
    logp = np.log(spx)
    r = logp.diff().rename("r")
    r2 = r ** 2
    roll = r2.rolling(window).sum()
    rv_trail = (TRADING_DAYS / window) * roll
    rv_fwd = (TRADING_DAYS / window) * roll.shift(-window)
    ret_fwd = logp.shift(-window) - logp
    df = pd.concat(
        [
            spx,
            r,
            vx,
            rv_trail.rename("rv_trail"),
            rv_fwd.rename("rv_fwd"),
            ret_fwd.rename("ret_fwd"),
        ],
        axis=1,
        join="inner",
    )
    df["K"] = (df["vix"] / 100.0) ** 2
    return df


def add_payoffs(df):
    """Per-window payoffs of the short side of a 30 day variance and volatility swap proxy."""
    df = df.copy()
    df["rv_capped"] = np.minimum(df["rv_fwd"], CAP_VARIANCE_MULT * df["K"])
    # Short variance swap, per unit of strike variance (premium received is 1.0).
    df["R_var"] = 1.0 - df["rv_fwd"] / df["K"]
    df["R_var_cap"] = 1.0 - df["rv_capped"] / df["K"]
    # Short volatility swap proxy, per unit of strike volatility.
    df["R_vol"] = 1.0 - np.sqrt(df["rv_fwd"]) / (df["vix"] / 100.0)
    df["vrp_volpts"] = df["vix"] - 100.0 * np.sqrt(df["rv_fwd"])
    # Ex-ante premium estimate using trailing realized variance as the forecast.
    df["vrp_exante"] = df["K"] - df["rv_trail"]
    return df


def payoff_with_cost(d, c, kind):
    """Short payoff when sold at (VIX - c) volatility points instead of the VIX mid.

    kind "var": per unit of strike variance. kind "vol": per unit of strike volatility.
    c is a stylized selling concession, not a measured transaction cost.
    """
    k_vol = (d["vix"] - c) / 100.0
    if kind == "var":
        return 1.0 - d["rv_fwd"] / (k_vol ** 2)
    if kind == "vol":
        return 1.0 - np.sqrt(d["rv_fwd"]) / k_vol
    raise ValueError(kind)


def nonoverlap(df, window=21, offset=0):
    """Every window-th observation so that forward windows do not overlap."""
    d = df.dropna(subset=["rv_fwd"])
    return d.iloc[offset::window]
