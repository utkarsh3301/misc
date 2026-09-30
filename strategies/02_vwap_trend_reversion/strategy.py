"""
Strategy 2: VWAP trend (primary) with VWAP reversion as a secondary,
regime-gated variant.

Primary (2A, Zarattini & Aziz style): trade in the direction of a close
crossing session VWAP, with a minimum distance band and a slope filter
so it does not flip on every touch. Exit on a close back across VWAP,
a hard premium stop, or the session time stop.

Secondary (2B, reversion): only in a range regime (flat VWAP, low ADX),
fade a close that is 2 standard deviations from VWAP back toward it.
Not implemented as code here since it needs a separate regime detector;
see README for the full spec if you want to build it out.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from common import indicators, monte_carlo, synthetic_data

CONFIG = {
    "instrument": "NIFTY",
    "lot_size": 65,
    "num_lots": 2,
    "assumed_entry_premium": 150.0,
    "band_atr_mult": 0.15,
    "slope_lookback": 15,
    "hard_stop_pct_of_entry": 0.20,
    "max_trades_per_day": 4,
    "flat_by": "15:10",
    # Monte Carlo assumptions from the research report: Zarattini & Aziz's
    # VWAP flip system hit about 17% with winners about 5x losers
    # (pre-slippage, QQQ). Indian post-cost evidence is thin. 30% win
    # rate / 5:1 payoff used here as a documented, conservative midpoint.
    "mc_win_rate": 0.30,
    "mc_avg_win_points": 30.0,
    "mc_avg_loss_points": 6.0,
}


def generate_signals(df):
    """
    df: 1-minute OHLCV DataFrame for one session.
    Returns 1 = call entry, -1 = put entry, 0 = no signal, on the bar the
    band is first crossed (not on every bar while still beyond it).
    """
    vwap = indicators.session_vwap(df)
    atr14 = indicators.atr(df, 14)
    dist = df["close"] - vwap
    band = CONFIG["band_atr_mult"] * atr14
    vwap_slope = vwap.diff(CONFIG["slope_lookback"])

    above_band = (dist > band) & (vwap_slope > 0)
    below_band = (dist < -band) & (vwap_slope < 0)

    call_entry = above_band & ~above_band.shift(1, fill_value=False)
    put_entry = below_band & ~below_band.shift(1, fill_value=False)

    signal = pd.Series(0, index=df.index)
    signal[call_entry] = 1
    signal[put_entry] = -1
    return signal


def demo():
    data = synthetic_data.generate_multi_day(n_days=20, seed=2)
    n_calls = n_puts = n_days = 0
    for _day, df in data.groupby("day"):
        n_days += 1
        sig = generate_signals(df)
        n_calls += int((sig == 1).sum())
        n_puts += int((sig == -1).sum())
    print(f"[demo] {n_days} synthetic sessions -> {n_calls} call signals, {n_puts} put signals "
          f"({(n_calls + n_puts) / n_days:.2f} signals/day). Synthetic data only, see README.")


def pop_simulation():
    return monte_carlo.simulate_pop(
        win_rate=CONFIG["mc_win_rate"],
        avg_win_points=CONFIG["mc_avg_win_points"],
        avg_loss_points=CONFIG["mc_avg_loss_points"],
        entry_premium=CONFIG["assumed_entry_premium"],
        lot_size=CONFIG["lot_size"],
        num_lots=CONFIG["num_lots"],
    )


if __name__ == "__main__":
    demo()
    r = pop_simulation()
    print(f"[pop] win_rate={r['win_rate_input']:.0%} -> POP over {r['n_trades']} trades = {r['pop']:.0%}, "
          f"expectancy/trade = Rs {r['expectancy_per_trade_rupees']:.1f}, "
          f"p05 drawdown = Rs {r['p05_max_drawdown_rupees']:.0f}")
