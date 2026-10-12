"""Compare an option-strategy return series with a benchmark, with inference that suits fat tails.

Built for the Cboe strategy indexes (PUT, BXM, CLL, ...) against a total-return equity index once
those series are available. It is tested here only on series that ship with this repo (S&P 500 and
Nasdaq composite), not on any option-strategy index. Inputs are periodic simple returns.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import stats_utils as su


def max_drawdown(r):
    eq = np.cumprod(1.0 + np.asarray(r, dtype=float))
    peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    return float((eq / peak - 1.0).min())


def sharpe_diff_t(sr1, sr2, years, rho):
    """Jobson-Korkie test of equal Sharpe ratios with the Memmel correction; annual units."""
    var = (1.0 / years) * (2.0 * (1.0 - rho) + 0.5 * (sr1 ** 2 + sr2 ** 2 - 2.0 * sr1 * sr2 * rho ** 2))
    return float((sr1 - sr2) / np.sqrt(var)) if var > 0 else float("nan")


def paired_bootstrap_sharpe_diff(s, b, ppy, block=6, reps=4000, seed=0):
    """Stationary paired bootstrap 95% interval for the annual Sharpe difference (strategy minus benchmark)."""
    rng = np.random.default_rng(seed)
    n = len(s)
    p = 1.0 / block
    out = np.empty(reps)
    for r in range(reps):
        idx = np.empty(n, dtype=np.int64)
        idx[0] = rng.integers(n)
        jumps = rng.random(n) < p
        starts = rng.integers(n, size=n)
        for t in range(1, n):
            idx[t] = starts[t] if jumps[t] else (idx[t - 1] + 1) % n
        ss, bb = s[idx], b[idx]
        out[r] = (ss.mean() / ss.std(ddof=1) - bb.mean() / bb.std(ddof=1)) * np.sqrt(ppy)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def compare(strategy, benchmark, rf_annual=0.0, periods_per_year=12, hac_lags=3, boot_reps=4000):
    """Return a dict of verification statistics for `strategy` against `benchmark` (both pd.Series of returns)."""
    df = pd.concat([strategy.rename("s"), benchmark.rename("b")], axis=1).dropna()
    ppy = periods_per_year
    rf = rf_annual / ppy
    s_ex = (df["s"] - rf).values
    b_ex = (df["b"] - rf).values
    n = len(df)
    years = n / ppy
    ds, db = su.describe(s_ex, ppy), su.describe(b_ex, ppy)
    rho = float(np.corrcoef(s_ex, b_ex)[0, 1])

    def ols(y, X):
        return sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})

    capm = ols(s_ex, b_ex)
    X2 = np.column_stack([np.minimum(b_ex, 0.0), np.maximum(b_ex, 0.0)])
    two = ols(s_ex, X2)
    quad = ols(s_ex, np.column_stack([b_ex, b_ex ** 2]))
    half = n // 2
    sub = {}
    for name, sl in (("first_half", slice(0, half)), ("second_half", slice(half, n))):
        a, c = s_ex[sl], b_ex[sl]
        sub[name] = float((a.mean() / a.std(ddof=1) - c.mean() / c.std(ddof=1)) * np.sqrt(ppy))
    lo, hi = paired_bootstrap_sharpe_diff(s_ex, b_ex, ppy, block=max(2, int(round(ppy / 2))), reps=boot_reps)
    sr_p = ds["sharpe_period"]
    return {
        "n": n,
        "years": years,
        "strategy": {k: float(ds[k]) for k in ("sharpe_annual", "skew", "kurtosis", "worst")},
        "benchmark": {k: float(db[k]) for k in ("sharpe_annual", "skew", "kurtosis", "worst")},
        "ann_excess_return": {"strategy": float(ds["mean"] * ppy), "benchmark": float(db["mean"] * ppy)},
        "ann_vol": {"strategy": float(ds["sd"] * np.sqrt(ppy)), "benchmark": float(db["sd"] * np.sqrt(ppy))},
        "max_drawdown": {"strategy": max_drawdown(df["s"].values), "benchmark": max_drawdown(df["b"].values)},
        "correlation": rho,
        "sharpe_difference": float(ds["sharpe_annual"] - db["sharpe_annual"]),
        "sharpe_difference_t_memmel": sharpe_diff_t(ds["sharpe_annual"], db["sharpe_annual"], years, rho),
        "sharpe_difference_boot95": [lo, hi],
        "capm": {
            "alpha_annual": float(capm.params[0] * ppy),
            "alpha_t_hac": float(capm.tvalues[0]),
            "beta": float(capm.params[1]),
            "r2": float(capm.rsquared),
        },
        "downside_vs_upside_beta": {
            "beta_down": float(two.params[1]),
            "beta_up": float(two.params[2]),
            "alpha_annual": float(two.params[0] * ppy),
            "alpha_t_hac": float(two.tvalues[0]),
        },
        "quadratic": {"mkt_sq_coef": float(quad.params[2]), "mkt_sq_t_hac": float(quad.tvalues[2]), "alpha_t_hac": float(quad.tvalues[0])},
        "subperiod_sharpe_difference": sub,
        "min_track_record_years_for_strategy_sharpe": float(su.min_track_record_periods(sr_p, ds["skew"], ds["kurtosis"]) / ppy),
    }
