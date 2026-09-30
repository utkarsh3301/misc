"""
Strategy 4: Supertrend trend follower gated by ADX/DMI.

Enter on a Supertrend flip, confirmed by ADX above a threshold and the
directional index agreeing with the flip. Exit on the next flip or a
hard premium stop, with no fixed target, since a trend system's edge
lives in letting winners run.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from common import indicators, monte_carlo, synthetic_data

CONFIG = {
    "instrument": "NIFTY",
    "lot_size": 65,
    "num_lots": 1,
    "assumed_entry_premium": 150.0,
    "supertrend_period": 10,
    "supertrend_mult": 3.0,
    "adx_period": 14,
    "adx_min": 20,
    "stop_pct_of_entry": 0.25,
    "max_trades_per_day": 3,
    "flat_by": "15:10",
    # Monte Carlo assumptions: an independent GitHub study of this exact
    # logic on Nifty 15-minute bars found a gross profit factor of 1.55,
    # falling to 1.27 after statutory charges alone (before slippage).
    # avg_win/avg_loss below reproduces that 1.27 figure at a 41% win
    # rate (0.41*36.5 / 0.59*20 = 1.27); see README for the slippage
    # sensitivity that pushed the same study toward breakeven.
    "mc_win_rate": 0.41,
    "mc_avg_win_points": 36.5,
    "mc_avg_loss_points": 20.0,
}


def generate_signals(df):
    """
    df: OHLC DataFrame (intended for 5 to 15-minute bars; synthetic demo
    uses 1-minute bars for simplicity).
    Returns 1 = call entry, -1 = put entry, 0 = no signal, on the bar the
    Supertrend flips with ADX/DMI confirmation.
    """
    _trend, direction = indicators.supertrend(df, CONFIG["supertrend_period"], CONFIG["supertrend_mult"])
    adx14, plus_di, minus_di = indicators.adx(df, CONFIG["adx_period"])

    flip_up = (direction == 1) & (direction.shift(1) == -1)
    flip_dn = (direction == -1) & (direction.shift(1) == 1)

    call_entry = flip_up & (adx14 > CONFIG["adx_min"]) & (plus_di > minus_di)
    put_entry = flip_dn & (adx14 > CONFIG["adx_min"]) & (minus_di > plus_di)

    signal = pd.Series(0, index=df.index)
    signal[call_entry] = 1
    signal[put_entry] = -1
    return signal


def demo():
    data = synthetic_data.generate_multi_day(n_days=20, seed=4)
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
