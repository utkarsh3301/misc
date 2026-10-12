"""Tests for the Design A put-writing harness on a small hand-built fixture.

The fixture is NOT market data and is not evidence about any strategy. Its purpose is to check the mechanics
(selection, fills, payoffs, collateral interest, skipping rules, look-ahead invariance) against answers
computed by hand. Run from the repo root:  PYTHONPATH=. python3 -m unittest discover -s tests -v
"""
import unittest

import numpy as np
import pandas as pd
from scipy.stats import norm

from src import putwrite as pw


def fixture_chain():
    rows = []

    def add(qd, ex, k, bid, ask, delta):
        rows.append(dict(quote_date=pd.Timestamp(qd), expiry=pd.Timestamp(ex), strike=k, cp="P", bid=bid, ask=ask, delta=delta))

    # Entry 1 on 2020-01-02: expiries 36 and 64 days out, target 35, so 2020-02-07 is chosen.
    for ex in ("2020-02-07", "2020-03-06"):
        add("2020-01-02", ex, 1800, 3.0, 3.4, -0.08)
        add("2020-01-02", ex, 1850, 6.0, 6.4, -0.16)
        add("2020-01-02", ex, 1900, 12.0, 12.5, -0.25)
    # Entry 2 on the first expiry day, 2020-02-07: expiries 28 and 56 days out, so 2020-03-06 is chosen.
    for ex in ("2020-03-06", "2020-04-03"):
        add("2020-02-07", ex, 1700, 2.5, 2.9, -0.08)
        add("2020-02-07", ex, 1750, 5.0, 5.5, -0.16)
        add("2020-02-07", ex, 1800, 11.0, 11.6, -0.30)
    return pd.DataFrame(rows)


SETTLE = pd.Series(
    {pd.Timestamp("2020-02-07"): 1900.0, pd.Timestamp("2020-03-06"): 1700.0, pd.Timestamp("2020-04-03"): 1650.0}
)
RATE = 0.02


class TestPutWriteMechanics(unittest.TestCase):
    def test_calendar_assumptions_of_the_fixture(self):
        self.assertEqual((pd.Timestamp("2020-02-07") - pd.Timestamp("2020-01-02")).days, 36)
        self.assertEqual((pd.Timestamp("2020-03-06") - pd.Timestamp("2020-01-02")).days, 64)
        self.assertEqual((pd.Timestamp("2020-03-06") - pd.Timestamp("2020-02-07")).days, 28)
        self.assertEqual((pd.Timestamp("2020-04-03") - pd.Timestamp("2020-02-07")).days, 56)

    def test_hand_computed_two_trades_at_the_bid(self):
        t = pw.put_write_backtest(fixture_chain(), SETTLE, RATE, target_dte=35, target_delta=0.16, fill="bid")
        self.assertEqual(len(t), 2)
        r1 = 6.0 / 1850.0 + RATE * 36 / 365.0  # expires worthless
        r2 = (5.0 - 50.0) / 1750.0 + RATE * 28 / 365.0  # settles 1700 against a 1750 strike
        self.assertEqual(list(t["strike"]), [1850.0, 1750.0])
        self.assertEqual(list(t["expiry"]), [pd.Timestamp("2020-02-07"), pd.Timestamp("2020-03-06")])
        self.assertAlmostEqual(t["return"].iloc[0], r1, places=12)
        self.assertAlmostEqual(t["return"].iloc[1], r2, places=12)

    def test_mid_fill_and_fees(self):
        t = pw.put_write_backtest(fixture_chain(), SETTLE, RATE, fill="mid", fee_per_contract=1.0)
        r1 = ((6.2 - 0.0) * 100 - 1.0) / (1850.0 * 100) + RATE * 36 / 365.0
        self.assertAlmostEqual(t["return"].iloc[0], r1, places=12)

    def test_selection_does_not_depend_on_settlement_values(self):
        a = pw.put_write_backtest(fixture_chain(), SETTLE, RATE)
        other = SETTLE.copy()
        other[:] = [1234.0, 5678.0, 91.0]
        b = pw.put_write_backtest(fixture_chain(), other, RATE)
        self.assertEqual(list(a["strike"]), list(b["strike"]))
        self.assertEqual(list(a["expiry"]), list(b["expiry"]))
        self.assertEqual(list(a["premium"]), list(b["premium"]))

    def test_missing_settlement_skips_the_entry(self):
        s = SETTLE.drop(pd.Timestamp("2020-02-07"))
        t = pw.put_write_backtest(fixture_chain(), s, RATE)
        self.assertEqual(len(t), 1)
        self.assertEqual(t["entry"].iloc[0], pd.Timestamp("2020-02-07"))

    def test_zero_bid_quotes_are_never_sold_at_the_bid(self):
        ch = fixture_chain()
        ch.loc[(ch["quote_date"] == "2020-01-02") & (ch["strike"] == 1850), "bid"] = 0.0
        t = pw.put_write_backtest(ch, SETTLE, RATE, fill="bid")
        # delta -0.16 had no bid, so the next closest absolute delta (-0.25 versus -0.08, gaps 0.09 and 0.08) is 1800
        self.assertEqual(t["strike"].iloc[0], 1800.0)

    def test_short_dated_expiries_below_min_dte_are_ignored(self):
        ch = fixture_chain()
        extra = ch[(ch["quote_date"] == "2020-01-02") & (ch["expiry"] == "2020-02-07")].copy()
        extra["expiry"] = pd.Timestamp("2020-01-06")  # 4 days out, the closest to target 35 only if min_dte were ignored
        extra["strike"] = extra["strike"] + 1
        t = pw.put_write_backtest(pd.concat([ch, extra]), SETTLE.combine_first(pd.Series({pd.Timestamp("2020-01-06"): 2000.0})), RATE, target_dte=2, min_dte=7)
        self.assertNotIn(pd.Timestamp("2020-01-06"), list(t["expiry"]))

    def test_black_scholes_delta_known_value_and_fallback_selection(self):
        self.assertAlmostEqual(pw.bs_put_delta(100.0, 100.0, 1.0, 0.0, 0.0, 0.2), norm.cdf(0.1) - 1.0, places=12)
        rows = []
        for k in (1700, 1800, 1900, 1950):
            rows.append(dict(quote_date=pd.Timestamp("2020-01-02"), expiry=pd.Timestamp("2020-02-07"), strike=float(k), cp="P", bid=5.0, ask=5.5, iv=0.18, underlying=2000.0))
        ch = pd.DataFrame(rows)
        t = pw.put_write_backtest(ch, pd.Series({pd.Timestamp("2020-02-07"): 2000.0}), 0.0, target_delta=0.16)
        deltas = {k: abs(pw.bs_put_delta(2000.0, float(k), 36 / 365.0, 0.0, 0.0, 0.18)) for k in (1700, 1800, 1900, 1950)}
        expected = min(deltas, key=lambda k: abs(deltas[k] - 0.16))
        self.assertEqual(t["strike"].iloc[0], float(expected))

    def test_next_entry_is_not_before_the_previous_expiry(self):
        t = pw.put_write_backtest(fixture_chain(), SETTLE, RATE)
        self.assertTrue((t["entry"].iloc[1:].values >= t["expiry"].iloc[:-1].values).all())

    def test_evaluate_runs_and_benchmark_alignment(self):
        # mechanics only: 24 monthly trades built from a deterministic pattern, not a claim about any market
        rows, settle = [], {}
        start = pd.Timestamp("2018-01-02")
        for i in range(24):
            qd = start + pd.Timedelta(days=35 * i)  # each trade starts on the previous expiry
            ex = qd + pd.Timedelta(days=35)
            for k, bid, d in ((1800.0, 3.0, -0.08), (1850.0, 6.0, -0.16), (1900.0, 12.0, -0.25)):
                rows.append(dict(quote_date=qd, expiry=ex, strike=k, cp="P", bid=bid, ask=bid + 0.4, delta=d))
            settle[ex] = 1700.0 if i % 7 == 3 else 1950.0
        ch = pd.DataFrame(rows)
        t = pw.put_write_backtest(ch, pd.Series(settle), 0.01)
        idx = pd.Series(2500.0 + 300.0 * np.sin(np.arange(1200) / 60.0), index=pd.date_range("2017-12-01", periods=1200, freq="D"))
        res = pw.evaluate(t, idx, rf_annual=0.01)
        self.assertEqual(len(t), 24)
        self.assertEqual(res["trades"]["n"], 24)
        self.assertAlmostEqual(res["trades"]["mean_days"], 35.0)
        self.assertIn("capm", res)
        self.assertTrue(np.isfinite(res["capm"]["beta"]))


class TestNoOverlappingPositions(unittest.TestCase):
    def test_monthly_quotes_with_35_day_trades_skip_alternate_months(self):
        rows, settle = [], {}
        start = pd.Timestamp("2018-01-02")
        for i in range(24):
            qd = start + pd.DateOffset(months=i)
            ex = qd + pd.Timedelta(days=35)
            for k, bid, d in ((1850.0, 6.0, -0.16),):
                rows.append(dict(quote_date=qd, expiry=ex, strike=k, cp="P", bid=bid, ask=bid + 0.4, delta=d))
            settle[ex] = 1950.0
        t = pw.put_write_backtest(pd.DataFrame(rows), pd.Series(settle), 0.0)
        self.assertEqual(len(t), 12)
        self.assertTrue((t["entry"].iloc[1:].values >= t["expiry"].iloc[:-1].values).all())


class TestCommandLinePlumbing(unittest.TestCase):
    def test_cli_runs_end_to_end_on_a_fixture(self):
        import importlib.util
        import os
        import tempfile

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        spec = importlib.util.spec_from_file_location("run_putwrite_backtest", os.path.join(root, "scripts", "run_putwrite_backtest.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rows, settle = [], {}
        start = pd.Timestamp("2018-01-02")
        for i in range(24):
            qd = start + pd.Timedelta(days=35 * i)  # each trade starts on the previous expiry
            ex = qd + pd.Timedelta(days=35)
            for k, bid, d in ((1800.0, 3.0, -0.08), (1850.0, 6.0, -0.16), (1900.0, 12.0, -0.25)):
                rows.append(dict(quote_date=qd.date(), expiry=ex.date(), strike=k, cp="P", bid=bid, ask=bid + 0.4, delta=d))
            settle[ex.date()] = 1700.0 if i % 7 == 3 else 1950.0
        idx = pd.Series(2500.0 + 300.0 * np.sin(np.arange(1200) / 60.0), index=pd.date_range("2017-12-01", periods=1200, freq="D"))
        with tempfile.TemporaryDirectory() as td:
            pd.DataFrame(rows).to_csv(os.path.join(td, "chain.csv"), index=False)
            pd.Series(settle, name="level").rename_axis("date").to_csv(os.path.join(td, "settle.csv"))
            idx.rename("level").rename_axis("date").to_csv(os.path.join(td, "bench.csv"))
            res = mod.main(
                ["--chain", os.path.join(td, "chain.csv"), "--settlement", os.path.join(td, "settle.csv"),
                 "--benchmark", os.path.join(td, "bench.csv"), "--rate", "0.01", "--out-dir", td]
            )
            self.assertTrue(os.path.exists(os.path.join(td, "putwrite_trades.csv")))
        self.assertEqual(res["trades"]["n"], 24)


if __name__ == "__main__":
    unittest.main()
