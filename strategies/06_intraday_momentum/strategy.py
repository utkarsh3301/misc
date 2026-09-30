"""
Strategy 6: Intraday time series momentum. First half-hour return
predicts the last half-hour return (Gao, Han, Li & Zhou, Journal of
Financial Economics, 2018). One decision per session, taken near the
close, trading in the direction of the opening move if it was large
enough to matter.

No published Nifty options implementation of this was found in the
research; treat this as the most speculative transfer in the set.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from common import monte_carlo, synthetic_data

CONFIG = {
    "instrument": "NIFTY",
    "lot_size": 65,
    "num_lots": 2,
    "assumed_entry_premium": 100.0,
    "opening_minutes": 30,
    "closing_minutes": 35,
    "signal_percentile": 0.60,  # trade only when |r1| is in the top 40% of recent sessions
    "flat_by": "15:20",
    # Monte Carlo assumptions: Gao et al. (JFE 2018) find the first
    # half-hour return predicts the last half-hour return with R^2 of
    # 1.6-3.3%, stronger on high volatility days. That translates to a
    # modest directional edge, not a large one; 52-56% used per the
    # README, midpoint below, with a correspondingly small R:R.
    "mc_win_rate": 0.54,
    "mc_avg_win_points": 10.0,
    "mc_avg_loss_points": 8.0,
}


def session_r1(df):
    """First-half-hour return for one session."""
    open_price = df["open"].iloc[0]
    r1_price = df["close"].iloc[min(CONFIG["opening_minutes"] - 1, len(df) - 1)]
    return r1_price / open_price - 1


def session_signal(df, r1_threshold):
    """One decision per session: 1 = call, -1 = put, 0 = no trade."""
    r1 = session_r1(df)
    if abs(r1) < r1_threshold:
        return 0, r1
    return (1 if r1 > 0 else -1), r1


def demo():
    data = synthetic_data.generate_multi_day(n_days=40, seed=6)
    r1_values = [session_r1(df) for _day, df in data.groupby("day")]
    threshold = float(np.quantile(np.abs(r1_values), CONFIG["signal_percentile"]))
    n_trades = sum(1 for r in r1_values if abs(r) >= threshold)
    print(f"[demo] {len(r1_values)} synthetic sessions, r1 threshold={threshold:.4%} -> "
          f"{n_trades} sessions would trigger a last-{CONFIG['closing_minutes']}-minute trade. "
          f"Synthetic data only, see README.")


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
