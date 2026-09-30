"""
Strategy 1: Dual EMA (9/21) crossover scalper, refined.

Original idea as given: 9 EMA vs 21 EMA on a 15-second chart, one order
every 1-2 minutes, buy calls on a bullish cross and puts on a bearish
cross, exit once "4 points" are banked.

Why it needed rework (full writeup in README.md): at 15-second
resolution the broker feed gives at most about 1 tick per second
(occasionally 2 for Nifty), so a 15-second bar is built from a handful
of already stale samples. A fixed 4-premium-point target on 1 lot needs
roughly a 70-75% win rate to break even after 2026 costs and slippage,
and published fast-MA-cross win rates run 25-35%. This module implements
the reworked version: 1-minute signal bars, trend/ADX/volatility
filters, and a target sized as a multiple of round trip cost with a
tighter stop than target.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from common import indicators, monte_carlo, synthetic_data

CONFIG = {
    "instrument": "NIFTY",
    "lot_size": 65,
    "num_lots": 3,
    "assumed_entry_premium": 120.0,
    "fast_ema": 9,
    "slow_ema": 21,
    "persistence_bars": 2,
    "min_spread_atr_mult": 0.15,
    "adx_period": 14,
    "adx_min": 20,
    "trade_windows": [("09:20", "11:30"), ("13:30", "14:45")],
    "flat_by": "15:10",
    "target_points": 4.0,
    "stop_points": 2.5,
    "time_stop_bars": 5,
    # Monte Carlo assumptions, sourced from the research report's Strategy 1
    # section: unfiltered fast crosses run 25-35% (Zarattini & Aziz MA9
    # table on 1-minute QQQ bars). The refined, filtered version is
    # estimated at 40-55%. Midpoint used below; see README for the range.
    "mc_win_rate": 0.475,
    "mc_avg_win_points": 4.0,
    "mc_avg_loss_points": 2.5,
}


def generate_signals(df):
    """
    df: 1-minute OHLCV DataFrame for one session.
    Returns a Series aligned to df.index: 1 = call entry, -1 = put entry,
    0 = no signal.

    Implementation note: the higher-timeframe trend filter here uses
    session VWAP only, as a simplification. Production should add the
    15-minute EMA21 slope confirmation described in the README for extra
    robustness against chop.
    """
    ema_fast = indicators.ema(df["close"], CONFIG["fast_ema"])
    ema_slow = indicators.ema(df["close"], CONFIG["slow_ema"])
    spread = ema_fast - ema_slow
    atr14 = indicators.atr(df, 14)
    vwap = indicators.session_vwap(df)
    adx14, _plus_di, _minus_di = indicators.adx(df, CONFIG["adx_period"])

    # "Persists for >= persistence_bars" means the entry fires once the
    # cross is confirmed, not at the instant of the raw cross itself (a
    # raw cross by definition has only 1 bar of history on the new side,
    # so ANDing persistence with the cross bar directly can never fire).
    n = CONFIG["persistence_bars"]
    confirmed_up = spread.gt(0).rolling(n).sum() >= n
    confirmed_dn = spread.lt(0).rolling(n).sum() >= n
    fresh_up = confirmed_up & ~confirmed_up.shift(1, fill_value=False)
    fresh_dn = confirmed_dn & ~confirmed_dn.shift(1, fill_value=False)

    spread_ok = spread.abs() > CONFIG["min_spread_atr_mult"] * atr14
    slope_up_ok = ema_slow.diff() > 0
    slope_dn_ok = ema_slow.diff() < 0
    trend_up_ok = df["close"] > vwap
    trend_dn_ok = df["close"] < vwap
    adx_ok = adx14 > CONFIG["adx_min"]

    times = df.index.strftime("%H:%M")
    in_window = pd.Series(False, index=df.index)
    for start, end in CONFIG["trade_windows"]:
        in_window |= (times >= start) & (times <= end)

    call_entry = fresh_up & spread_ok & slope_up_ok & trend_up_ok & adx_ok & in_window
    put_entry = fresh_dn & spread_ok & slope_dn_ok & trend_dn_ok & adx_ok & in_window

    signal = pd.Series(0, index=df.index)
    signal[call_entry] = 1
    signal[put_entry] = -1
    return signal


def demo():
    """Sanity check the signal logic on synthetic bars. Not a performance test."""
    data = synthetic_data.generate_multi_day(n_days=20, seed=1)
    n_calls = n_puts = n_days = 0
    for _day, df in data.groupby("day"):
        n_days += 1
        sig = generate_signals(df)
        n_calls += int((sig == 1).sum())
        n_puts += int((sig == -1).sum())
    print(f"[demo] {n_days} synthetic sessions -> {n_calls} call signals, {n_puts} put signals "
          f"({(n_calls + n_puts) / n_days:.2f} signals/day). Synthetic data only, see module docstring.")


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
