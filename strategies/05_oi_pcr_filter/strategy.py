"""
Strategy 5: Open interest build-up and PCR as a directional filter.

The research found weak standalone evidence for OI/PCR-based entries;
the credible use is as a confirmation or veto layer on top of a price
based trigger (Strategies 1, 3 or 4), not as a standalone engine. This
module implements it that way: a filter function plus a synthetic OI/PCR
proxy so the filter logic has something to run against in the demo. Wire
apply_oi_filter() to your broker's live option chain OI feed, and a real
base signal, before using this for anything real.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd

from common import indicators, monte_carlo, synthetic_data

CONFIG = {
    "instrument": "NIFTY",
    "lot_size": 65,
    "num_lots": 2,
    "assumed_entry_premium": 150.0,
    "pcr_confirm_window": 3,
    "pcr_rising_threshold": 0.02,
    # No standalone win rate exists in the evidence (see README). This
    # models the research's "a few percentage points of uplift" as an
    # explicit, labelled assumption rather than a measured result: a
    # base price signal at 45%, and the same signal at 50% when OI/PCR
    # confirmed.
    "mc_win_rate_unfiltered": 0.45,
    "mc_win_rate_oi_confirmed": 0.50,
    "mc_avg_win_points": 30.0,
    "mc_avg_loss_points": 20.0,
}


def synthetic_oi_pcr_proxy(df, seed=0):
    """Fake OI/futures build-up proxy correlated with recent price direction, demo only."""
    rng = np.random.default_rng(seed)
    price_change = df["close"].diff().fillna(0)
    smoothed = price_change.rolling(5).mean().fillna(0)
    noise = rng.normal(0, price_change.std() * 2 if price_change.std() > 0 else 1.0, len(df))
    oi_change_proxy = -smoothed * rng.uniform(0.5, 1.5) + noise
    pcr_change_proxy = -np.sign(smoothed) * rng.uniform(0, 0.03, len(df))
    return pd.DataFrame({
        "oi_change_proxy": oi_change_proxy,
        "pcr_change_proxy": pcr_change_proxy,
    }, index=df.index)


def apply_oi_filter(signal, oi_pcr_df):
    """Pass a directional signal through only when the OI/PCR proxy agrees."""
    confirmed = signal.copy()
    pcr_rising = oi_pcr_df["pcr_change_proxy"].rolling(CONFIG["pcr_confirm_window"]).sum() > CONFIG["pcr_rising_threshold"]
    pcr_falling = oi_pcr_df["pcr_change_proxy"].rolling(CONFIG["pcr_confirm_window"]).sum() < -CONFIG["pcr_rising_threshold"]
    confirmed[(signal == 1) & ~pcr_rising] = 0
    confirmed[(signal == -1) & ~pcr_falling] = 0
    return confirmed


def demo():
    data = synthetic_data.generate_multi_day(n_days=20, seed=5)
    n_raw = n_confirmed = n_days = 0
    for day, df in data.groupby("day"):
        n_days += 1
        ema9 = indicators.ema(df["close"], 9)
        base_signal = pd.Series(0, index=df.index)
        cross_up = (df["close"] > ema9) & (df["close"].shift(1) <= ema9.shift(1))
        cross_dn = (df["close"] < ema9) & (df["close"].shift(1) >= ema9.shift(1))
        base_signal[cross_up] = 1
        base_signal[cross_dn] = -1

        oi_pcr = synthetic_oi_pcr_proxy(df, seed=int(day))
        confirmed = apply_oi_filter(base_signal, oi_pcr)
        n_raw += int((base_signal != 0).sum())
        n_confirmed += int((confirmed != 0).sum())

    pass_rate = n_confirmed / max(n_raw, 1)
    print(f"[demo] {n_days} synthetic sessions -> {n_raw} raw price signals, {n_confirmed} OI-confirmed "
          f"({pass_rate:.0%} pass rate). Synthetic OI/PCR proxy, not real option chain data.")


def pop_simulation():
    unfiltered = monte_carlo.simulate_pop(
        win_rate=CONFIG["mc_win_rate_unfiltered"],
        avg_win_points=CONFIG["mc_avg_win_points"],
        avg_loss_points=CONFIG["mc_avg_loss_points"],
        entry_premium=CONFIG["assumed_entry_premium"],
        lot_size=CONFIG["lot_size"],
        num_lots=CONFIG["num_lots"],
        seed=50,
    )
    oi_confirmed = monte_carlo.simulate_pop(
        win_rate=CONFIG["mc_win_rate_oi_confirmed"],
        avg_win_points=CONFIG["mc_avg_win_points"],
        avg_loss_points=CONFIG["mc_avg_loss_points"],
        entry_premium=CONFIG["assumed_entry_premium"],
        lot_size=CONFIG["lot_size"],
        num_lots=CONFIG["num_lots"],
        seed=51,
    )
    return {"unfiltered": unfiltered, "oi_confirmed": oi_confirmed}


if __name__ == "__main__":
    demo()
    results = pop_simulation()
    for name, r in results.items():
        print(f"[pop:{name}] win_rate={r['win_rate_input']:.0%} -> POP over {r['n_trades']} trades = {r['pop']:.0%}, "
              f"expectancy/trade = Rs {r['expectancy_per_trade_rupees']:.1f}")
