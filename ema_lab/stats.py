"""
Significance tests used in the report.

random_entry_test is the important one for crossover systems. A long
only rule in a market that rose 12x will look profitable no matter how
it times entries, so the question is whether its timing beats random
timing with the same number of trades, the same holding periods and the
same long/short mix. The p-value is the share of random strategies whose
mean trade return is at least as good as the real one.
"""

import numpy as np
from scipy import stats as sps


def bootstrap_mean_ci(x, n_boot=5000, alpha=0.05, seed=0):
    x = np.asarray(x, float)
    if len(x) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
    return np.quantile(means, alpha / 2), np.quantile(means, 1 - alpha / 2)


def t_test_mean(x):
    """One sided t-test of mean > 0. Returns (t, p)."""
    x = np.asarray(x, float)
    if len(x) < 3 or x.std() == 0:
        return np.nan, np.nan
    t, p = sps.ttest_1samp(x, 0.0, alternative="greater")
    return float(t), float(p)


def binomial_p(successes, n, p0, alternative="greater"):
    if n == 0:
        return np.nan
    return float(sps.binomtest(int(successes), int(n), p0, alternative=alternative).pvalue)


def random_entry_pooled(items, n_sims=1000, seed=0, same_day=False):
    """
    Random entry test pooled over several instruments. items is a list of
    (df, trades, cost); each random strategy redraws every instrument's
    trades at random times on that instrument, keeping holding periods and
    directions, and the pooled mean trade is compared with the real one.
    same_day=True keeps random trades inside one session.
    """
    items = [(df, t, cost) for df, t, cost in items if len(t)]
    if not items:
        return {"p_value": np.nan, "real_mean": np.nan, "random_mean": np.nan, "random_p95": np.nan}
    rng = np.random.default_rng(seed)
    real = np.concatenate([t["ret"].to_numpy() for _, t, _ in items]).mean()
    prepared = []
    for df, t, cost in items:
        day = df.index.normalize().to_numpy() if same_day else None
        prepared.append((df["open"].to_numpy(np.float64), df["close"].to_numpy(np.float64),
                         t["bars"].to_numpy(), t["direction"].to_numpy(), cost, day))
    total = sum(len(p[2]) for p in prepared)

    sims = np.empty(n_sims)
    for k in range(n_sims):
        acc = 0.0
        for o, c, bars, dirs, cost, day in prepared:
            start = rng.integers(0, len(c) - bars)
            end = start + bars - 1
            if day is not None:
                bad = day[start] != day[end]
                tries = 0
                while bad.any() and tries < 50:
                    start[bad] = rng.integers(0, len(c) - bars[bad])
                    end = start + bars - 1
                    bad = day[start] != day[end]
                    tries += 1
            gross = dirs * (c[end] / o[start] - 1.0)
            acc += ((1.0 + gross) * (1.0 - cost) ** 2 - 1.0).sum()
        sims[k] = acc / total
    return {
        "p_value": float((np.sum(sims >= real) + 1) / (n_sims + 1)),
        "real_mean": float(real),
        "random_mean": float(sims.mean()),
        "random_p95": float(np.quantile(sims, 0.95)),
    }


def random_entry_test(df, trades, cost, n_sims=1000, seed=0, same_day=False):
    """
    Monte Carlo of random entry times that keep each real trade's holding
    period and direction, for one instrument.
    """
    return random_entry_pooled([(df, trades, cost)], n_sims=n_sims, seed=seed, same_day=same_day)


def expected_max_sharpe(n_trials, sharpe_std):
    """
    Expected best Sharpe ratio among n_trials strategies with zero true
    skill, given the cross-sectional std of their Sharpe ratios (Bailey
    and Lopez de Prado, "The Deflated Sharpe Ratio", 2014). A grid's best
    result below this is consistent with luck.
    """
    if n_trials < 2:
        return 0.0
    gamma = 0.5772156649
    z1 = sps.norm.ppf(1 - 1.0 / n_trials)
    z2 = sps.norm.ppf(1 - 1.0 / (n_trials * np.e))
    return sharpe_std * ((1 - gamma) * z1 + gamma * z2)
