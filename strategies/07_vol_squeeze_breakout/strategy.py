"""
Strategy 7: Volatility-regime-gated squeeze breakout.

Bollinger Band width squeezing inside the Keltner Channel marks
compressed realised volatility. A breakout from that squeeze, on rising
volume, is a common practitioner setup. The evidence-backed part is the
regime gate around it (skip rich-IV days and event days, since implied
volatility carries a negative variance risk premium on average); the
breakout entry itself is a hypothesis, not something the research found
a rigorous published Nifty backtest for.
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
    "assumed_entry_premium": 130.0,
    "bb_period": 20,
    "bb_std": 2.0,
    "kc_period": 20,
    "kc_mult": 1.5,
    "squeeze_width_lookback_bars": 200,
    "squeeze_pctile": 0.20,
    "volume_mult": 1.5,
    "flat_by": "15:10",
    # Monte Carlo assumptions: no rigorous post-cost Nifty backtest of the
    # breakout entry was found; the win rate below matches other
    # breakout systems in the set (24-49% range across US and India
    # evidence) and the R:R matches a typical breakout profile.
    "mc_win_rate": 0.40,
    "mc_avg_win_points": 33.0,
    "mc_avg_loss_points": 15.0,
}


def generate_signals(df):
    """
    df: OHLCV DataFrame, intended for 5-minute bars (synthetic demo uses
    1-minute bars, with a wider lookback window to compensate).
    Returns 1 = call entry, -1 = put entry, 0 = no signal.
    """
    bb_low, _bb_mid, bb_up = indicators.bollinger(df, CONFIG["bb_period"], CONFIG["bb_std"])
    kc_low, _kc_mid, kc_up = indicators.keltner(df, CONFIG["kc_period"], CONFIG["kc_mult"])
    bb_width = bb_up - bb_low

    width_threshold = bb_width.rolling(CONFIG["squeeze_width_lookback_bars"]).quantile(CONFIG["squeeze_pctile"])
    narrow = bb_width <= width_threshold
    squeeze = (bb_up < kc_up) & (bb_low > kc_low) & narrow

    vol_ok = df["volume"] > CONFIG["volume_mult"] * df["volume"].rolling(20).median()
    breakout_up = (df["close"] > bb_up) & squeeze.shift(1, fill_value=False)
    breakout_dn = (df["close"] < bb_low) & squeeze.shift(1, fill_value=False)

    call_entry = breakout_up & vol_ok
    put_entry = breakout_dn & vol_ok
    call_entry = call_entry & ~call_entry.shift(1, fill_value=False)
    put_entry = put_entry & ~put_entry.shift(1, fill_value=False)

    signal = pd.Series(0, index=df.index)
    signal[call_entry] = 1
    signal[put_entry] = -1
    return signal


def demo():
    data = synthetic_data.generate_multi_day(n_days=20, seed=7)
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
