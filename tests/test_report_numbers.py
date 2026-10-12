"""Every number quoted in REPORT.md is regenerated from results/ and must appear in the report text.

Hand-typed numbers drift when analyses are re-run. This test builds the expected strings from the results
files (and from the pure functions in scripts/run_published_stats_arithmetic.py) using the same rounding the
report uses, and fails with the missing string if the report disagrees. Run after the analysis scripts:
    PYTHONPATH=. python3 -m unittest tests.test_report_numbers -v
"""
import csv
import importlib.util
import json
import os
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def J(name):
    with open(os.path.join(ROOT, "results", name)) as f:
        return json.load(f)


def rows_csv(path):
    with open(os.path.join(ROOT, path)) as f:
        return list(csv.DictReader(f))


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "scripts", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestReportMatchesResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(os.path.join(ROOT, "results", "vrp_summary.json")):
            raise unittest.SkipTest("results/ missing: run bash run_all.sh first")
        with open(os.path.join(ROOT, "REPORT.md")) as f:
            cls.report = f.read()
        cls.v = J("vrp_summary.json")
        cls.r = J("vrp_robustness.json")
        cls.c = J("conditional_rules.json")
        cls.p = J("power_analysis.json")
        cls.t = J("tail_frequency.json")
        cls.s = J("variance_by_session.json")
        cls.e = J("event_check.json")
        cls.a = J("data_audit.json")

    def has(self, *strings):
        for s in strings:
            self.assertTrue(s in self.report, f"REPORT.md does not contain: {s!r}")

    # ---- section 3
    def test_environment_and_audit_numbers(self):
        f5 = self.e["feb5_2018"]
        self.has(
            f"{f5['prev_vix']:.2f} to {f5['vix']:.2f} (+{100 * f5['change']:.1f}%)",
            f"low of {self.e['sanity']['vix_min']:.2f} on 2017-11-03",
            f"high of {self.e['sanity']['vix_max']:.2f} on {self.e['sanity']['vix_max_date']}",
            f"correlation {self.a['vix_spx_alignment']['corr_dlogvix_vs_spx_return_by_lag']['0']:.2f}",
            f"correlates {self.a['french_vs_spx_monthly']['correlation']:.3f} with the S&P 500 monthly price return over {self.a['french_vs_spx_monthly']['months']} months",
        )

    # ---- section 4.1
    def test_premium_section(self):
        v, r = self.v, self.r
        p = v["premium"]
        ot = v["offset_table"]
        self.has(
            f"The sample has {v['coverage']['daily_windows']:,} daily 21-trading-day windows ({v['coverage']['nonoverlap_windows']} non-overlapping)",
            f"Mean VIX {p['mean_vix']:.1f} against mean realized volatility {p['mean_realized_vol_forward']:.1f}: a gap of {p['mean_vrp_volpts']:.1f} vol points",
            f"above realized volatility in {100 * p['share_windows_vix_above_realized']:.1f}% of windows",
            f"Realized variance averaged {100 * p['realized_over_strike_var_ratio']:.0f}% of the strike variance",
            f"mean payoff +{ot['R_var']['mean_per_window']:.3f} of the strike per window",
            f"Annualized Sharpe {ot['R_var']['sharpe_mean_over_offsets']:.2f} averaged over the 21 possible monthly window grids (range {ot['R_var']['sharpe_min']:.2f} to {ot['R_var']['sharpe_max']:.2f})",
            f"Volatility proxy: Sharpe {ot['R_vol']['sharpe_mean_over_offsets']:.2f} (range {ot['R_vol']['sharpe_min']:.2f} to {ot['R_vol']['sharpe_max']:.2f})",
        )
        shares = [r["window_sensitivity"][k]["vix_above_realized"] for k in r["window_sensitivity"]]
        self.has(f"({100 * min(shares):.1f}% to {100 * max(shares):.1f}% for 20 to 22 day windows)")
        hac = r["hac_lag_sensitivity"]
        tv = [hac[k]["R_var_t"] for k in hac]
        tl = [hac[k]["R_vol_t"] for k in hac]
        b_var = v["offset0"]["R_var"]["t_newey_west_daily_overlapping"]
        b_vol = v["offset0"]["R_vol"]["t_newey_west_daily_overlapping"]
        self.has(f"HAC t = {b_var:.1f} for the variance proxy ({min(tv):.1f} to {max(tv):.1f} across 10 to 63 lags) and {b_vol:.1f} for the volatility proxy ({min(tl):.1f} to {max(tl):.1f})")
        npv = r["null_bootstrap_pvalues"]["var"]
        self.has(f"one-sided p = {npv['offset0']:.3f} for the variance proxy (worst start grid {npv['max_other_offsets']:.3f})")
        by = v["by_year"]
        self.has("2014 {:+.2f}, 2015 {:+.2f}, 2016 {:+.2f}, 2017 {:+.2f}, 2018 {:+.2f}".format(*[by[y]["mean_R_var"] for y in ("2014", "2015", "2016", "2017", "2018")]))
        fc = v["forecasting"]
        self.has(
            f"is {fc['mincer_zarnowitz_slope_on_K']:.2f} (t = {fc['mincer_zarnowitz_slope_t_vs_one']:.1f} against 1), R-squared {fc['mincer_zarnowitz_r2']:.2f}",
            f"R-squared {100 * fc['ret_on_exante_vrp_r2']:.1f}% (t = {fc['ret_on_exante_vrp_t']:.2f})",
        )
        tt = r["vix_tercile_table"]
        lo, mid, hi = tt["low"], tt["middle"], tt["high"]
        self.has(
            f"{lo['mean_gap_volpts']:.1f} vol points when the VIX started at {lo['vix_min']:.1f} to {lo['vix_max']:.1f}, {mid['mean_gap_volpts']:.1f} at {mid['vix_min']:.1f} to {mid['vix_max']:.1f} and {hi['mean_gap_volpts']:.1f} at {hi['vix_min']:.1f} to {hi['vix_max']:.1f}",
            f"worst payoff {lo['worst_R_var']:.1f}, against {hi['worst_R_var']:.1f} in the top tercile",
        )
        rb = r["range_based_realized_variance"]
        self.has(f"({rb['mean_gap_volpts_range_based']:.1f} vol points, t = {rb['t_nw_R_var_range_based']:.1f}) but averages only {100 * rb['mean_ratio_range_over_close_variance']:.0f}% of")

    # ---- section 4.2
    def test_payoff_shape_section(self):
        v, r = self.v, self.r
        o = v["offset0"]["R_var"]
        self.has(f"{100 * o['share_positive']:.0f}% of windows gain. Skew is {o['skew']:.1f} and kurtosis {o['kurtosis']:.1f}.")
        w = v["worst_offset0"]
        months = {"01": "Jan", "08": "Aug", "10": "Oct"}
        for d in ("2015-08-05", "2018-01-04", "2018-10-04"):
            row = w[d]
            y, m, dd = d.split("-")
            label = f"{int(dd)} {months[m]} {y}"
            self.has(label)
            self.has(f"({'payoff ' if d == '2015-08-05' else ''}{row['R_var']:.2f}")
        row = w["2015-08-05"]
        simple = float(np.expm1(row["ret_fwd"]))
        self.has(f"VIX {row['vix']:.1f}, delivered {row['rv_vol']:.1f}, S&P 500 {100 * simple:.1f}%")
        wa = list(v["worst_any_offset"].values())[0]
        self.has(f"at {wa['R_var']:.2f} ({wa['R_var_cap']:.2f} if the swap is capped")
        lev = r["leverage_view"]
        self.has(f"{lev['R_var']['months_of_mean_gain_lost_in_worst_window']:.1f} months of average gains for the variance proxy and {lev['R_vol']['months_of_mean_gain_lost_in_worst_window']:.1f} for the volatility proxy")
        t10 = [x for x in lev["R_var"]["table"] if abs(x["target_vol"] - 0.10) < 1e-9][0]
        t30 = [x for x in lev["R_var"]["table"] if abs(x["target_vol"] - 0.30) < 1e-9][0]
        yrs = v["verifiability"]["R_var"]["years_in_sample"]
        self.has(
            f"worst month of {100 * t10['worst_month']:.1f}%, a maximum drawdown of {100 * t10['max_drawdown']:.1f}% and a CAGR of {100 * t10['cagr']:.1f}% (final value ${t10['final_equity']:.2f} over {yrs:.1f} years)",
            f"the worst month is {100 * t30['worst_month']:.1f}%",
        )
        me = v["market_exposure"]["R_var"]
        self.has(
            f"beta +{me['beta']:.0f} per unit of 21-day S&P 500 log return (t = {me['beta_t']:.1f}) and a squared-return coefficient of {me['quad_mkt_sq_coef']:.0f} (t = {me['quad_mkt_sq_t']:.1f}), R-squared {me['r2_linear']:.2f} rising to {me['r2_quadratic']:.2f}",
            f"(t = {me['alpha_t']:.1f} on the monthly grid)",
        )

    # ---- section 4.3
    def test_cost_section(self):
        r = self.r
        ct = r["cost_table"]
        be = r["breakeven_cost_volpts"]
        self.has(
            f"+{ct['0.0']['var_mean']:.3f} at c = 0 to +{ct['1.0']['var_mean']:.3f} at c = 1.0 and {ct['2.0']['var_mean']:.3f} at c = 2.0",
            f"The break-even concession is {be['var']:.2f} vol points",
            f"For the volatility proxy the break-even is {be['vol']:.2f}",
        )
        if not os.path.exists(os.path.join(ROOT, "results", "figures", "data", "fig3_cost_sensitivity.csv")):
            self.skipTest("figure data missing: run scripts/make_figures.py (or bash run_all.sh) first")
        data = rows_csv("results/figures/data/fig3_cost_sensitivity.csv")
        x = [float(d["concession_volpts"]) for d in data]

        def cross(col):
            y = [float(d[col]) for d in data]
            for i in range(len(y) - 1):
                if y[i] >= 1.96 > y[i + 1]:
                    return x[i] + (y[i] - 1.96) / (y[i] - y[i + 1]) * (x[i + 1] - x[i])

        self.has(f"the HAC t falls below 1.96 after {cross('t_short_variance'):.1f}", f"significance goes after {cross('t_short_volatility'):.1f}")

    # ---- section 4.4
    def test_calm_sample_section(self):
        t, v = self.t, self.v
        fb = t["five_year_blocks"]
        self.has(
            f"Mean 21-day realized volatility was {t['2014-2018']['mean']:.1f} in 2014 to 2018 against {t['1999-2018']['mean']:.1f} over 1999 to 1999".replace("1999 to 1999", "1999 to 2018"),
            f"ranks {fb['rank_of_2014_block']}nd calmest of {fb['n_blocks']} rolling five-year blocks (2013 to 2017 is calmer at {fb['mean_by_start_year']['2013']:.1f})",
            f"{100 * t['share_by_level']['40']['share_1999_2018']:.1f}% of all windows",
            f"{100 * t['worst_21d_log_return']['1999-2018']:.1f}% against {100 * t['worst_21d_log_return']['2014-2018']:.1f}% inside the window",
        )
        pk = [e[2] for e in t["episodes_rv40"]]
        self.has(f"2002 (peak {pk[0]:.0f}), September 2002 ({pk[1]:.0f}), 2008 ({pk[2]:.0f}), 2009 ({pk[3]:.0f}) and 2011 ({pk[4]:.0f})")
        be = t["breakeven_strike"]
        avg_strike = float(np.sqrt(v["premium"]["mean_strike_var_pts"]))
        self.has(
            f"Over 1999 to 2018 it is {be['1999-2018']['breakeven_strike']:.1f} vol points against a mean realized volatility of {be['1999-2018']['mean_realized_vol']:.1f}",
            f"excluding 2008 and 2009 it is {be['excluding 2008-2009']['breakeven_strike']:.1f}",
            f"in 2014 to 2018 it was {be['2014-2018']['breakeven_strike']:.1f} against an average strike of {avg_strike:.1f} in variance terms (mean VIX {v['premium']['mean_vix']:.1f})",
        )
        g = t["payoff_grid_arithmetic"]
        self.has(f"{g['RV 40']['VIX 15']:.1f} at realized volatility 40, {g['RV 60']['VIX 15']:.1f} at 60 and {g['RV 80']['VIX 15']:.1f} at 80")

    # ---- section 4.5
    def test_verifiability_section(self):
        v, p = self.v, self.p
        ver = v["verifiability"]["R_var"]
        ci = ver["ci95_block_bootstrap"]
        fr = v["fragility"]["R_var"]
        self.has(
            f"Sharpe {ver['sharpe_annual']:.2f} with a Mertens standard error of {ver['se_annual_mertens']:.2f} and a bootstrap 95% interval of {ci[0]:.2f} to {ci[1]:.2f}",
            f"{ver['years_needed_t1645_with_sample_moments']:.1f} years of data are needed",
            f"({ver['years_needed_t1645_if_normal']:.1f} if returns were normal)",
            f"The sample has {ver['years_in_sample']:.1f} years",
            f"lifts the Sharpe from {fr['sharpe_all']:.2f} to {fr['sharpe_drop_worst_window']:.2f}",
            f"gives {fr['sharpe_ex_janfeb2018_starts']:.2f}",
        )
        rows = rows_csv("results/rolling_premium_verifiability.csv")

        def get(series, years, col):
            return float([d for d in rows if d["series"] == series and int(d["window_years"]) == years][0][col])

        pc = lambda x: f"{100 * x:.0f}%"
        m5, m10, m20, m30 = (get("Mkt-RF", y, "share_t_above_1.96") for y in (5, 10, 20, 30))
        self.has(
            f"only {pc(m5)} of rolling 5-year windows have t above 1.96 ({pc(get('Mkt-RF', 5, 'share_mean_negative'))} have a negative mean), {pc(m10)} of 10-year, {pc(m20)} of 20-year and {pc(m30)} of 30-year windows",
            "Value: " + ", ".join(pc(get("HML", y, "share_t_above_1.96")) for y in (5, 10, 20, 30)),
            f"Size: {pc(get('SMB', 5, 'share_t_above_1.96'))} at 5 years and {pc(get('SMB', 30, 'share_t_above_1.96'))} at 30 years",
        )
        an = p["analytic_years"]
        self.has(
            f"{p['power']['normal']['0.5']['5'] * 100:.0f}% of the time under normal returns",
            f"{an['0.5']['years_80pct_normal']:.0f} (normal) and {an['0.5']['years_80pct_shortvol_shape']:.0f} (short-volatility shape) at a true Sharpe of 0.5; {an['1.0']['years_80pct_normal']:.1f} and {an['1.0']['years_80pct_shortvol_shape']:.0f} at a true Sharpe of 1.0",
        )
        fp = p["power"]["empirical_shape"]["0.0"]
        self.has(f"passes the one-sided 5% test {fp['3'] * 100:.0f}%, {fp['5'] * 100:.0f}% and {fp['10'] * 100:.0f}% of the time at 3, 5 and 10 years")

    # ---- section 4.6
    def test_rule_table(self):
        tab = self.c["table"]
        names = {
            "R0_always_sell": "R0 always sell",
            "R1_vix_above_1y_median": "R1 VIX above its 1-year median",
            "R2_exante_vrp_positive": "R2 ex-ante premium positive",
            "R3_vix_below_20": "R3 VIX below 20",
            "R4_vol_managed_cap2": "R4 volatility-managed (cap 2x)",
            "R5_skip_after_loss_below_minus1": "R5 skip after a loss below -1",
        }
        for k, label in names.items():
            x = tab[k]
            self.has(
                f"| {label} | {100 * x['share_invested']:.0f}% | {x['sharpe_offset0']:.2f} | {x['sharpe_avg_21_grids']:.2f} | {x['sharpe_grid_min']:.2f} to {x['sharpe_grid_max']:.2f} | {x['sharpe_in_sample_offset0']:.2f} | {x['sharpe_out_of_sample_offset0']:.2f} | {x['worst_month']:.2f} |"
            )
        r0, r1, r5 = tab["R0_always_sell"], tab["R1_vix_above_1y_median"], tab["R5_skip_after_loss_below_minus1"]
        dsr = list(self.c["deflated_sharpe_grid_average"].values())
        self.has(
            f"(R1, in-sample Sharpe {r1['sharpe_in_sample_offset0']:.2f}) earned {r1['sharpe_out_of_sample_offset0']:.2f} out of sample against {r0['sharpe_out_of_sample_offset0']:.2f} for always selling",
            f"(R5, {r5['sharpe_out_of_sample_offset0']:.2f}) differs from always selling by {abs(r5['sharpe_out_of_sample_offset0'] - r0['sharpe_out_of_sample_offset0']):.2f}",
            f"ranges from {r1['sharpe_grid_min']:.2f} to {r1['sharpe_grid_max']:.2f}",
            f"are {min(dsr):.2f} to {max(dsr):.2f} for every rule",
        )

    # ---- section 4.7
    def test_weekend_section(self):
        w = self.s["weekend_vs_ordinary_c2c"]
        ab = [w[k]["mean_abs_return_ratio"] for k in w]
        self.has(
            f"is {w['1999-2018']['variance_ratio']:.2f} times an ordinary day over 1999 to 2018 ({w['ex 2008-2009']['variance_ratio']:.2f} excluding 2008 and 2009, {w['1999-2007']['variance_ratio']:.2f} in 1999 to 2007, {w['2010-2018']['variance_ratio']:.2f} in 2010 to 2018)",
            f"Mean absolute returns give {min(ab):.2f} to {max(ab):.2f}",
        )

    # ---- section 4.8
    def test_published_statistics_arithmetic(self):
        m = load_script("run_published_stats_arithmetic")
        t = [m.sr_diff_t(0.67, 0.47, 29.5, rho) for rho in (0.80, 0.85, 0.90, 0.95)]
        self.has(f"t = {t[0]:.1f}, {t[1]:.1f}, {t[2]:.2f} and {t[3]:.1f} for assumed correlations")
        sr_put = (0.0940 - 0.034) / 0.1026
        sr_spx = (0.0991 - 0.034) / 0.1538
        ts = [m.sr_diff_t(sr_put, sr_spx, 37.1, rho) for rho in (0.80, 0.85, 0.90, 0.95)]
        self.has(f"the Sharpe ratios are {sr_put:.2f} and {sr_spx:.2f} and t ranges from {min(ts):.1f} to {max(ts):.1f}")
        a = {rf: m.capm_alpha(0.100, 0.101, 0.55, rf, 0.101, 0.153, 31.0) for rf in (0.025, 0.045)}
        self.has(f"{100 * a[0.045][0]:.1f}% to {100 * a[0.025][0]:.1f}% a year, iid t of {a[0.045][2]:.1f} to {a[0.025][2]:.1f}")


if __name__ == "__main__":
    unittest.main()
