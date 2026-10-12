"""Correctness tests. Run from the repo root:  PYTHONPATH=. python3 -m unittest discover -s tests -v"""
import importlib.util
import os
import unittest

import numpy as np
import pandas as pd
from arch.data import sp500

from src import stats_utils as su
from src import vrp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "scripts", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRealizedVarianceAlignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = vrp.load_frame(21)
        cls.spx = sp500.load()["Close"]
        cls.r = np.log(cls.spx).diff()

    def test_forward_rv_uses_only_the_next_21_returns(self):
        valid = self.df.dropna(subset=["rv_fwd"]).index
        for t in valid[[0, 50, 400, 900, len(valid) - 1]]:
            pos = self.spx.index.get_loc(t)
            expected = 252.0 / 21 * float((self.r.iloc[pos + 1 : pos + 22] ** 2).sum())
            self.assertAlmostEqual(self.df.loc[t, "rv_fwd"], expected, places=12)

    def test_trailing_rv_uses_only_the_last_21_returns(self):
        valid = self.df.dropna(subset=["rv_trail"]).index
        for t in valid[[0, 50, 400, 900, len(valid) - 1]]:
            pos = self.spx.index.get_loc(t)
            expected = 252.0 / 21 * float((self.r.iloc[pos - 20 : pos + 1] ** 2).sum())
            self.assertAlmostEqual(self.df.loc[t, "rv_trail"], expected, places=12)

    def test_forward_return_matches_price_ratio(self):
        valid = self.df.dropna(subset=["ret_fwd"]).index
        t = valid[100]
        pos = self.spx.index.get_loc(t)
        self.assertAlmostEqual(self.df.loc[t, "ret_fwd"], float(np.log(self.spx.iloc[pos + 21] / self.spx.iloc[pos])), places=12)


class TestPayoffs(unittest.TestCase):
    def test_payoff_formulas(self):
        df = pd.DataFrame({"vix": [20.0], "K": [0.04], "rv_fwd": [0.09], "rv_trail": [0.02]})
        out = vrp.add_payoffs(df)
        self.assertAlmostEqual(out["R_var"].iloc[0], 1 - 0.09 / 0.04)
        self.assertAlmostEqual(out["R_vol"].iloc[0], 1 - 0.3 / 0.2)
        self.assertAlmostEqual(out["vrp_volpts"].iloc[0], 20.0 - 30.0)
        # cap binds at 6.25 x strike variance
        df2 = pd.DataFrame({"vix": [10.0], "K": [0.01], "rv_fwd": [0.5], "rv_trail": [0.01]})
        self.assertAlmostEqual(vrp.add_payoffs(df2)["R_var_cap"].iloc[0], 1 - 6.25)

    def test_nonoverlap_windows_do_not_overlap(self):
        df = vrp.add_payoffs(vrp.load_frame(21))
        m = vrp.nonoverlap(df, 21, 3)
        pos = [df.index.get_loc(i) for i in m.index]
        self.assertTrue(all(b - a == 21 for a, b in zip(pos[:-1], pos[1:])))


class TestStatsUtils(unittest.TestCase):
    def test_sharpe_se_matches_iid_normal_formula(self):
        sr, n = 0.2, 120
        self.assertAlmostEqual(su.sharpe_se(sr, n, 0.0, 3.0), np.sqrt((1 + 0.5 * sr ** 2) / (n - 1)))

    def test_sharpe_se_is_larger_with_negative_skew(self):
        self.assertGreater(su.sharpe_se(0.3, 60, -3.0, 15.0), su.sharpe_se(0.3, 60, 0.0, 3.0))

    def test_min_track_record_known_value(self):
        # Bailey and Lopez de Prado: 1 + [1 - skew*SR + (kurt-1)/4*SR^2] * (z/SR)^2.
        # For normal returns the bracket is 1 + SR^2/2.
        sr, z = 0.25, 1.645
        expected = 1 + (1 + 0.5 * sr ** 2) * (z / sr) ** 2
        self.assertAlmostEqual(su.min_track_record_periods(sr, 0.0, 3.0, z=z), expected, places=9)

    def test_expected_max_sharpe_grows_with_trials(self):
        a, b = su.expected_max_sharpe(5, 0.01), su.expected_max_sharpe(500, 0.01)
        self.assertGreater(b, a)
        self.assertEqual(su.expected_max_sharpe(1, 0.01), 0.0)

    def test_newey_west_t_close_to_naive_for_white_noise(self):
        rng = np.random.default_rng(1)
        x = rng.normal(0.1, 1.0, 4000)
        naive = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
        self.assertLess(abs(su.newey_west_t(x, 5) - naive), 0.2)


class TestNoLookAheadInRules(unittest.TestCase):
    def test_weights_do_not_change_when_the_future_is_removed(self):
        rules = load_script("run_conditional_rules")
        cutoff = "2017-06-30"
        full = vrp.add_payoffs(vrp.load_frame(21)).dropna(subset=["vix"])
        cut = vrp.add_payoffs(vrp.load_frame(21, end=cutoff)).dropna(subset=["vix"])
        _, w_full = rules.build_weights(full)
        _, w_cut = rules.build_weights(cut)
        compared = 0
        for k in w_full:
            a = w_full[k].loc[:cutoff]
            b = w_cut[k].loc[:cutoff]
            both = a.index.intersection(b.index)
            # skip the warm-up rows where rolling medians are NaN in both
            mask = a.loc[both].notna() & b.loc[both].notna()
            self.assertTrue(mask.sum() > 300, k)
            diff = (a.loc[both][mask] - b.loc[both][mask]).abs().max()
            self.assertLess(diff, 1e-12, f"{k} changes when future data is removed")
            compared += 1
        self.assertEqual(compared, 6)


class TestIndexCompare(unittest.TestCase):
    """Smoke and sanity tests on bundled EQUITY series only (S&P 500 and Nasdaq composite)."""

    @classmethod
    def setUpClass(cls):
        from arch.data import nasdaq

        cls.spx = sp500.load()["Close"].pct_change().dropna()
        cls.ndx = nasdaq.load()["Close"].pct_change().dropna()

    def test_identical_series_have_unit_beta_and_zero_alpha(self):
        from src import index_compare as ic

        res = ic.compare(self.spx, self.spx, periods_per_year=252, hac_lags=5, boot_reps=200)
        self.assertAlmostEqual(res["capm"]["beta"], 1.0, places=9)
        self.assertAlmostEqual(res["capm"]["alpha_annual"], 0.0, places=9)
        self.assertAlmostEqual(res["sharpe_difference"], 0.0, places=9)

    def test_nasdaq_has_beta_above_one_and_sane_outputs(self):
        from src import index_compare as ic

        res = ic.compare(self.ndx, self.spx, periods_per_year=252, hac_lags=5, boot_reps=200)
        self.assertGreater(res["capm"]["beta"], 1.0)
        self.assertLess(res["capm"]["beta"], 1.6)
        self.assertTrue(0.6 < res["correlation"] < 1.0)
        lo, hi = res["sharpe_difference_boot95"]
        self.assertLess(lo, hi)
        self.assertLess(res["max_drawdown"]["strategy"], 0.0)

    def test_sharpe_difference_test_matches_hand_formula(self):
        from src import index_compare as ic

        sr1, sr2, yrs, rho = 0.67, 0.47, 29.5, 0.9
        hand = (sr1 - sr2) / np.sqrt((1 / yrs) * (2 * (1 - rho) + 0.5 * (sr1 ** 2 + sr2 ** 2 - 2 * sr1 * sr2 * rho ** 2)))
        self.assertAlmostEqual(ic.sharpe_diff_t(sr1, sr2, yrs, rho), hand, places=12)
        self.assertAlmostEqual(hand, 2.05, places=2)


if __name__ == "__main__":
    unittest.main()
