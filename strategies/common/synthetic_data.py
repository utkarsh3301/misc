"""
Synthetic intraday OHLCV generator. Used only to sanity check that each
strategy's signal logic runs end to end on realistic shaped bars.

This is not a historical or empirical proxy for Nifty or Bank Nifty. No
real tick or options data feed was reachable from this environment (the
outbound network here is allowlisted to package registries and GitHub
only, confirmed by a failed Yahoo Finance request during development).
Treat any statistics computed from this data as a mechanics demo, not a
performance claim. The actual probability of profit numbers in each
strategy's README come from the Monte Carlo cost simulation
(common/monte_carlo.py), seeded with win rate and reward to risk
assumptions sourced from the research report, not from this generator.
"""

import numpy as np
import pandas as pd

MINUTES_PER_SESSION = 375  # 09:15 to 15:30 IST


def _intraday_vol_multiplier(n):
    """U shaped intraday volatility: higher near open/close, lower midday."""
    x = np.linspace(-1, 1, n)
    return 0.7 + 0.6 * (x ** 2)


def generate_session(seed, start_price=24000.0, daily_vol=0.012,
                      regime="random", n_minutes=MINUTES_PER_SESSION):
    """
    One synthetic trading session of 1-minute OHLCV bars.

    regime: "trend_up", "trend_down", "chop" or "random" (picks one of
    the first three with equal probability). This exists only so the
    demo signal code has some directional days to fire on. It carries no
    claim about how often real Nifty/Bank Nifty days actually trend.
    """
    rng = np.random.default_rng(seed)
    if regime == "random":
        regime = rng.choice(["trend_up", "trend_down", "chop"])

    drift_per_min = {"trend_up": 0.00003, "trend_down": -0.00003, "chop": 0.0}[regime]
    minute_vol = daily_vol / np.sqrt(n_minutes)
    vol_mult = _intraday_vol_multiplier(n_minutes)

    rets = rng.normal(drift_per_min, minute_vol, n_minutes) * vol_mult
    close = start_price * np.cumprod(1 + rets)
    open_ = np.concatenate([[start_price], close[:-1]])
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.0006, n_minutes))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.0006, n_minutes))
    base_vol = rng.uniform(800, 2500, n_minutes) * vol_mult
    volume = base_vol.astype(int)

    idx = pd.date_range("2026-01-01 09:15", periods=n_minutes, freq="1min")
    df = pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    }, index=idx)
    return df, regime


def generate_multi_day(n_days, seed=0, start_price=24000.0, daily_vol=0.012):
    sessions = []
    price = start_price
    for d in range(n_days):
        df, regime = generate_session(seed=seed + d, start_price=price, daily_vol=daily_vol)
        df["day"] = d
        df["regime"] = regime
        sessions.append(df)
        price = df["close"].iloc[-1]
    return pd.concat(sessions)
