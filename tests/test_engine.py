"""
Execution rule tests for ema_lab.engine. Run: python -m pytest tests
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ema_lab import engine, metrics


def bars(rows):
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df.index = pd.date_range("2024-01-01", periods=len(df), freq="D")
    df["volume"] = 0.0
    return df


def flags(n, *idx):
    a = np.zeros(n, dtype=bool)
    a[list(idx)] = True
    return a


FLAT = [[100, 101, 99, 100]] * 6


def test_signal_fills_next_open_and_holds_to_end():
    df = bars([[100, 101, 99, 100], [102, 106, 101, 105], [105, 108, 104, 107], [107, 110, 106, 110]])
    r = engine.run(df, {"long_entry": flags(4, 0)})
    t = r.trades.iloc[0]
    assert t.entry_i == 1 and t.entry_price == 102
    assert t.exit_reason == "end" and t.exit_price == 110
    assert r.returns.iloc[0] == 0.0  # no look-ahead: the signal bar earns nothing
    assert np.isclose((1 + r.returns).prod(), 110 / 102)


def test_stop_fills_at_level_and_gap_fills_at_open():
    df = bars([[100, 101, 99, 100], [100, 101, 96, 97], [100, 101, 99, 100]])
    r = engine.run(df, {"long_entry": flags(3, 0), "stop_dist": np.full(3, 2.0)})
    assert r.trades.iloc[0].exit_price == 98 and r.trades.iloc[0].exit_reason == "stop"

    df = bars([[100, 101, 99, 100], [100, 101, 99.5, 100], [95, 96, 94, 95]])
    r = engine.run(df, {"long_entry": flags(3, 0), "stop_dist": np.full(3, 2.0)})
    assert r.trades.iloc[0].exit_price == 95  # gapped through 98, filled at the open


def test_stop_wins_when_bar_hits_both_levels():
    df = bars([[100, 101, 99, 100], [100, 106, 97, 100], [100, 101, 99, 100]])
    r = engine.run(df, {"long_entry": flags(3, 0), "stop_dist": np.full(3, 2.0),
                        "target_dist": np.full(3, 5.0)})
    assert r.trades.iloc[0].exit_reason == "stop"


def test_short_target_and_time_stop():
    df = bars([[100, 101, 99, 100], [100, 100.5, 94, 95], [100, 101, 99, 100]])
    r = engine.run(df, {"short_entry": flags(3, 0), "target_dist": np.full(3, 5.0)})
    t = r.trades.iloc[0]
    assert t.direction == -1 and t.exit_price == 95 and t.exit_reason == "target"
    assert np.isclose(t.ret, 0.05)

    r = engine.run(bars(FLAT), {"long_entry": flags(6, 0), "max_bars": 3})
    t = r.trades.iloc[0]
    assert t.entry_i == 1 and t.exit_i == 3 and t.exit_reason == "time"


def test_session_flat_blocks_overnight_orders():
    df = bars(FLAT)
    sig = {"long_entry": flags(6, 0, 2), "flat_at_close": flags(6, 2)}
    r = engine.run(df, sig)
    assert len(r.trades) == 1
    assert r.trades.iloc[0].exit_i == 2 and r.trades.iloc[0].exit_reason == "session"


def test_reversal_and_costs():
    df = bars([[100, 101, 99, 100], [100, 111, 99, 110], [110, 111, 99, 100], [100, 101, 89, 90]])
    sig = {"long_entry": flags(4, 0), "short_entry": flags(4, 1)}
    r = engine.run(df, sig, cost=0.001)
    assert list(r.trades.direction) == [1, -1]
    assert r.trades.iloc[0].exit_price == 110 and r.trades.iloc[1].entry_price == 110
    expected = (1.10 * 0.999 ** 2 - 1, (1 + (1 - 90 / 110)) * 0.999 ** 2 - 1)
    assert np.allclose(r.trades.ret, expected)
    # equity compounds bar returns: two round trips, four fills
    assert np.isclose((1 + r.returns).prod(), 1.10 * (2 - 100 / 110) * (1 - (90 / 100 - 1)) * 0.999 ** 4)


def test_trade_stats():
    trades = pd.DataFrame({"ret": [0.10, -0.05, -0.05, 0.02], "bars": [5, 3, 3, 2]})
    s = metrics.trade_stats(trades)
    assert s["win_rate"] == 0.5
    assert np.isclose(s["profit_factor"], 0.12 / 0.10)
    assert s["max_consec_losses"] == 2


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
