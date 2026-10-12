"""Independent recomputation of the headline premium numbers with plain loops.

No pandas rolling windows and no statsmodels: realized variance is summed by an explicit loop and the
Newey-West t-statistic uses a hand-written Bartlett estimator. The results must match results/vrp_summary.json.
Run from the repo root:  PYTHONPATH=. python3 -m unittest discover -s tests -v
"""
import json
import os
import unittest

import numpy as np
from arch.data import sp500, vix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def nw_t(x, lags):
    x = np.asarray(x, dtype=float)
    n = len(x)
    m = x.mean()
    e = x - m
    s2 = float((e * e).sum()) / n
    for l in range(1, lags + 1):
        w = 1.0 - l / (lags + 1.0)
        s2 += 2.0 * w * float((e[l:] * e[:-l]).sum()) / n
    return m / np.sqrt(s2 / n)


class TestIndependentRecompute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spx = sp500.load()["Close"]
        vx = vix.load()["vix"].dropna()
        dates = [d for d in vx.index if d in spx.index]
        px = {d: float(spx.loc[d]) for d in spx.index}
        spx_dates = list(spx.index)
        pos = {d: i for i, d in enumerate(spx_dates)}
        closes = np.array([px[d] for d in spx_dates])
        lr = np.zeros(len(closes))
        for i in range(1, len(closes)):
            lr[i] = np.log(closes[i] / closes[i - 1])
        r_var, r_vol, gap, rv_vol = [], [], [], []
        joined = [d for d in dates]
        # windows measured in trading days of the joined VIX and S&P 500 dates, as in src/vrp.py
        jpos = {d: i for i, d in enumerate(joined)}
        for d in joined:
            i = jpos[d]
            if i + 21 >= len(joined):
                break
            ret_idx = [pos[joined[i + k]] for k in range(1, 22)]
            ss = 0.0
            for j in ret_idx:
                ss += lr[j] ** 2
            rv = 252.0 / 21.0 * ss
            k_var = (float(vx.loc[d]) / 100.0) ** 2
            r_var.append(1.0 - rv / k_var)
            r_vol.append(1.0 - np.sqrt(rv) / (float(vx.loc[d]) / 100.0))
            gap.append(float(vx.loc[d]) - 100.0 * np.sqrt(rv))
            rv_vol.append(100.0 * np.sqrt(rv))
        cls.r_var, cls.r_vol, cls.gap, cls.rv_vol = map(np.array, (r_var, r_vol, gap, rv_vol))
        path = os.path.join(ROOT, "results", "vrp_summary.json")
        if not os.path.exists(path):
            raise unittest.SkipTest("results/vrp_summary.json missing: run scripts/run_vrp_study.py (or bash run_all.sh) first")
        with open(path) as f:
            cls.res = json.load(f)

    def test_window_count(self):
        self.assertEqual(len(self.r_var), self.res["coverage"]["daily_windows"])

    def test_mean_gap_and_share(self):
        self.assertAlmostEqual(float(self.gap.mean()), self.res["premium"]["mean_vrp_volpts"], places=9)
        self.assertAlmostEqual(float((self.gap > 0).mean()), self.res["premium"]["share_windows_vix_above_realized"], places=9)

    def test_mean_payoffs(self):
        self.assertAlmostEqual(float(self.r_var.mean()), self.res["offset_table"]["R_var"]["mean_per_window"], delta=5e-4)
        self.assertAlmostEqual(float(self.r_vol.mean()), self.res["offset_table"]["R_vol"]["mean_per_window"], delta=5e-4)

    def test_newey_west_t_matches_statsmodels(self):
        self.assertAlmostEqual(nw_t(self.r_var, 20), self.res["offset0"]["R_var"]["t_newey_west_daily_overlapping"], places=2)
        self.assertAlmostEqual(nw_t(self.r_vol, 20), self.res["offset0"]["R_vol"]["t_newey_west_daily_overlapping"], places=2)

    def test_offset0_sharpe_and_skew(self):
        m0 = self.r_var[0::21]
        sr = m0.mean() / m0.std(ddof=1) * np.sqrt(12)
        self.assertAlmostEqual(float(sr), self.res["offset0"]["R_var"]["sharpe_annual"], places=6)
        self.assertEqual(len(m0), int(self.res["offset0"]["R_var"]["n"]))


if __name__ == "__main__":
    unittest.main()
