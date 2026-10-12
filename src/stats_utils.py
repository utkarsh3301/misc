"""Statistics helpers for judging whether a return stream shows a verifiable edge.

Formulas follow:
  Lo (2002), The Statistics of Sharpe Ratios.
  Mertens (2002), non-normal correction to the Sharpe standard error.
  Bailey and Lopez de Prado (2012, 2014), minimum track record length and
  the deflated Sharpe ratio.
"""
import numpy as np
import statsmodels.api as sm
from scipy import stats

EULER_GAMMA = 0.5772156649015329


def describe(x, periods_per_year):
    """Basic moments of a per-period return series."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    mean = x.mean()
    sd = x.std(ddof=1)
    sr = mean / sd
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "sharpe_period": sr,
        "sharpe_annual": sr * np.sqrt(periods_per_year),
        "t_naive": mean / (sd / np.sqrt(n)),
        "skew": stats.skew(x, bias=False),
        "kurtosis": stats.kurtosis(x, fisher=False, bias=False),
        "worst": x.min(),
        "best": x.max(),
        "share_positive": (x > 0).mean(),
    }


def newey_west_t(x, lags):
    """t-stat of the mean with Newey-West (HAC) standard errors."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    res = sm.OLS(x, np.ones_like(x)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.tvalues[0])


def sharpe_variance_factor(sr, skew, kurt):
    """n * Var(SR_hat) for iid returns with given skew and raw kurtosis (Mertens 2002)."""
    return 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2


def sharpe_se(sr, n, skew, kurt):
    return float(np.sqrt(sharpe_variance_factor(sr, skew, kurt) / (n - 1)))


def min_track_record_periods(sr, skew, kurt, z=1.645, sr_null=0.0):
    """Periods needed before SR_hat exceeds sr_null at one-sided confidence z."""
    if sr <= sr_null:
        return float("inf")
    return 1.0 + sharpe_variance_factor(sr, skew, kurt) * (z / (sr - sr_null)) ** 2


def expected_max_sharpe(n_trials, var_trial_sharpes):
    """Expected best Sharpe among n_trials strategies with no skill."""
    if n_trials <= 1:
        return 0.0
    return float(
        np.sqrt(var_trial_sharpes)
        * (
            (1 - EULER_GAMMA) * stats.norm.ppf(1 - 1.0 / n_trials)
            + EULER_GAMMA * stats.norm.ppf(1 - 1.0 / (n_trials * np.e))
        )
    )


def deflated_sharpe(sr, n, skew, kurt, n_trials, var_trial_sharpes):
    """Probability that the true Sharpe beats the best-of-n_trials luck benchmark."""
    sr0 = expected_max_sharpe(n_trials, var_trial_sharpes)
    se = sharpe_se(sr, n, skew, kurt)
    return float(stats.norm.cdf((sr - sr0) / se))


def power_normal(sr_annual, years, periods_per_year=12, z=1.645):
    """P(t > z) for normal returns with a given TRUE annual Sharpe ratio (large-sample approximation)."""
    n = years * periods_per_year
    ncp = sr_annual / np.sqrt(periods_per_year) * np.sqrt(n)
    return float(1.0 - stats.norm.cdf(z - ncp))


def power_empirical_shape(shape, sr_annual, years, rng, reps=6000, periods_per_year=12, z=1.645):
    """P(t > z) when returns are drawn from an empirical shape, standardized then shifted to a TRUE Sharpe.

    HYPOTHETICAL power analysis: with sr_annual = 0 this is the false-positive rate of the naive t-test.
    """
    x = np.asarray(shape, dtype=float)
    x = (x - x.mean()) / x.std(ddof=1)
    sr_p = sr_annual / np.sqrt(periods_per_year)
    n = int(round(years * periods_per_year))
    draws = rng.choice(x, size=(reps, n), replace=True) + sr_p
    t = draws.mean(axis=1) / (draws.std(axis=1, ddof=1) / np.sqrt(n))
    return float((t > z).mean())


def block_bootstrap_ci(x, func, block, reps=5000, size=0.95, seed=0):
    """Stationary-bootstrap percentile confidence interval for func(x)."""
    from arch.bootstrap import StationaryBootstrap

    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    bs = StationaryBootstrap(block, x, seed=seed)
    ci = bs.conf_int(func, reps=reps, method="percentile", size=size)
    return float(ci[0, 0]), float(ci[1, 0])
