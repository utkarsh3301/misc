"""
Kyle (1985) single-period insider trading model.

An informed trader observes the true liquidation value v ~ N(0, sigma_v^2) exactly
(v0 = 0 without loss of generality) and submits order size x = beta * v. Noise
traders submit u ~ N(0, sigma_u^2), independent of v. A risk-neutral, competitive
market maker observes only total order flow y = x + u (not x and u separately) and
sets price p = lambda * y = E[v | y].

Equilibrium (beta*, lambda*) is a mutual best response:
  - Informed trader's optimum given lambda:      beta  = 1 / (2 * lambda)
  - Market maker's zero-profit pricing given beta: lambda = beta * sigma_v^2 /
                                                             (beta^2 sigma_v^2 + sigma_u^2)
Solving jointly gives the closed form used below (derivation in quant-trading-models.md).
"""

import numpy as np


def kyle_equilibrium(sigma_v, sigma_u):
    """Closed-form Kyle (1985) equilibrium: (lambda, beta, expected informed profit)."""
    lam = sigma_v / (2 * sigma_u)
    beta = sigma_u / sigma_v
    expected_profit = 0.5 * sigma_u * sigma_v
    return lam, beta, expected_profit


def simulate_kyle(sigma_v, sigma_u, n_sims=2_000_000, seed=0):
    """
    Monte Carlo check of the equilibrium: simulate the game at the theoretical
    (lambda*, beta*), then verify
      1) the market maker's pricing rule is really E[v|y]  (regression slope of v on y)
      2) the informed trader's realized average profit matches the closed form.
    """
    rng = np.random.default_rng(seed)
    lam, beta, theo_profit = kyle_equilibrium(sigma_v, sigma_u)

    v = rng.normal(0.0, sigma_v, n_sims)
    u = rng.normal(0.0, sigma_u, n_sims)
    x = beta * v
    y = x + u
    p = lam * y

    # Empirical E[v|y] slope via OLS: Cov(v,y)/Var(y), should equal lambda*.
    cov_vy = np.cov(v, y)[0, 1]
    var_y = np.var(y)
    empirical_lambda = cov_vy / var_y

    informed_profit = (v - p) * x
    empirical_profit = informed_profit.mean()

    return {
        "lambda_theory": lam,
        "lambda_empirical": empirical_lambda,
        "beta_theory": beta,
        "profit_theory": theo_profit,
        "profit_empirical": empirical_profit,
        "price_efficiency_check": np.corrcoef(p, v)[0, 1],  # price should track value
    }


if __name__ == "__main__":
    for sigma_v, sigma_u in [(1.0, 1.0), (2.0, 1.0), (1.0, 4.0)]:
        result = simulate_kyle(sigma_v, sigma_u)
        print(f"sigma_v={sigma_v}, sigma_u={sigma_u}")
        print(f"  lambda: theory={result['lambda_theory']:.4f}  "
              f"empirical={result['lambda_empirical']:.4f}")
        print(f"  informed profit: theory={result['profit_theory']:.4f}  "
              f"empirical={result['profit_empirical']:.4f}")
        print(f"  corr(price, true value) = {result['price_efficiency_check']:.4f}")
        print()
