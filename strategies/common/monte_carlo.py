"""
Cost aware Monte Carlo simulator for probability of profit (POP).

This answers a narrower, more honest question than "backtest this
strategy on history": given a win rate and reward to risk ratio taken
from the research report's cited evidence for a strategy family, and the
real 2026 NSE options cost model, what is the probability the strategy
is net profitable over a run of N trades, and what does the drawdown
distribution look like.

It does not claim to know the true win rate. Each strategy's README
states where its win_rate, avg_win_points and avg_loss_points inputs
come from, and run_sensitivity() shows how POP moves if those
assumptions turn out to be wrong.
"""

import numpy as np

from . import costs


def simulate_pop(win_rate, avg_win_points, avg_loss_points, entry_premium,
                  lot_size, num_lots, n_trades=250, n_runs=4000,
                  slippage_points_per_side=0.5, outcome_std_frac=0.3, seed=42):
    rng = np.random.default_rng(seed)
    final_pnl = np.empty(n_runs)
    max_dd = np.empty(n_runs)

    for i in range(n_runs):
        wins = rng.random(n_trades) < win_rate
        win_mag = np.clip(rng.normal(avg_win_points, avg_win_points * outcome_std_frac, n_trades), 0.25, None)
        loss_mag = np.clip(rng.normal(avg_loss_points, avg_loss_points * outcome_std_frac, n_trades), 0.25, None)
        point_pnl = np.where(wins, win_mag, -loss_mag)

        exit_premium = entry_premium + point_pnl
        cost = costs.round_trip_cost(entry_premium, exit_premium, lot_size, num_lots,
                                      slippage_points_per_side)
        gross_rupees = point_pnl * lot_size * num_lots
        net_rupees = gross_rupees - cost["total_cost_rupees"]

        cum = np.cumsum(net_rupees)
        final_pnl[i] = cum[-1]
        running_max = np.maximum.accumulate(cum)
        max_dd[i] = (cum - running_max).min()

    return {
        "win_rate_input": win_rate,
        "avg_win_points": avg_win_points,
        "avg_loss_points": avg_loss_points,
        "n_trades": n_trades,
        "n_runs": n_runs,
        "pop": float((final_pnl > 0).mean()),
        "mean_pnl_rupees": float(final_pnl.mean()),
        "median_pnl_rupees": float(np.median(final_pnl)),
        "p05_pnl_rupees": float(np.percentile(final_pnl, 5)),
        "p95_pnl_rupees": float(np.percentile(final_pnl, 95)),
        "expectancy_per_trade_rupees": float(final_pnl.mean() / n_trades),
        "mean_max_drawdown_rupees": float(max_dd.mean()),
        "p05_max_drawdown_rupees": float(np.percentile(max_dd, 5)),
    }


def run_sensitivity(base_kwargs, win_rate_grid):
    """POP as win_rate varies, holding everything else fixed."""
    rows = []
    for wr in win_rate_grid:
        kwargs = dict(base_kwargs)
        kwargs["win_rate"] = wr
        result = simulate_pop(**kwargs)
        rows.append((wr, result["pop"], result["expectancy_per_trade_rupees"]))
    return rows
