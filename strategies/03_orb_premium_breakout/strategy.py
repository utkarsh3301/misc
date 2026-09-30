"""
Strategy 3: Opening range breakout on the option premium.

This is the best India-specific evidence in the set. Zerodha's own post
cost backtest (Jan 2022 to Feb 2026) on Nifty weekly option buying showed
about a 48% win rate with a max drawdown near 45%. The design: pick the
CE and PE closest to a Rs 200 premium at market open, track each
premium's opening range high/low, then buy a breakout of its own range
with a 20% premium stop and no fixed target.

Reference note: this module applies the ORB logic directly to whatever
price series it is given (see demo(), which uses the synthetic index
proxy). In production, run generate_signals() on the actual CE/PE
premium series, not the index, per the original study's design.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from common import monte_carlo, synthetic_data

CONFIG = {
    "instrument": "NIFTY",
    "lot_size": 65,
    "num_lots": 2,
    "assumed_entry_premium": 200.0,  # matches the Zerodha ORB study's strike selection
    "or_window_minutes": 120,        # 09:15 to 11:15
    "stop_pct_of_entry": 0.20,
    "flat_by": "15:15",
    "max_trades_per_day": 2,
    # Monte Carlo assumptions: Zerodha, "The Long and the Short", In The
    # Money by Zerodha, 10 Mar 2026: ~48% win rate, post cost, with a
    # profit factor of about 1.23. avg_win/avg_loss below reproduces that
    # profit factor at this win rate (0.48*40 / 0.52*30 = 1.23).
    "mc_win_rate": 0.48,
    "mc_avg_win_points": 40.0,
    "mc_avg_loss_points": 30.0,
}


def generate_signals(df):
    """
    df: 1-minute OHLC series for one session (index or option premium).
    Returns 1 = call/long entry, -1 = put/short-side entry, 0 = none, on
    the first bar that breaks the opening range.
    """
    or_end = df.index[0] + pd.Timedelta(minutes=CONFIG["or_window_minutes"])
    or_slice = df[df.index < or_end]
    or_high = or_slice["high"].max()
    or_low = or_slice["low"].min()

    post = df.index >= or_end
    break_up = pd.Series(False, index=df.index)
    break_dn = pd.Series(False, index=df.index)
    break_up[post] = df.loc[post, "close"] > or_high
    break_dn[post] = df.loc[post, "close"] < or_low

    call_raw = break_up & ~break_up.shift(1, fill_value=False)
    put_raw = break_dn & ~break_dn.shift(1, fill_value=False)

    # Only the first breakout of each side counts (matches "max 2 trades
    # per day": one CE breakout and one PE breakout, not every re-break).
    call_entry = pd.Series(False, index=df.index)
    put_entry = pd.Series(False, index=df.index)
    if call_raw.any():
        call_entry.loc[call_raw.idxmax()] = True
    if put_raw.any():
        put_entry.loc[put_raw.idxmax()] = True

    signal = pd.Series(0, index=df.index)
    signal[call_entry] = 1
    signal[put_entry] = -1
    return signal


def demo():
    data = synthetic_data.generate_multi_day(n_days=20, seed=3)
    n_calls = n_puts = n_days = 0
    for _day, df in data.groupby("day"):
        n_days += 1
        sig = generate_signals(df)
        n_calls += int((sig == 1).sum())
        n_puts += int((sig == -1).sum())
    print(f"[demo] {n_days} synthetic sessions -> {n_calls} call signals, {n_puts} put signals "
          f"({(n_calls + n_puts) / n_days:.2f} signals/day). Applied to the synthetic index proxy, "
          f"not real option premium series, see module docstring.")


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
