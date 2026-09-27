"""
Cournot competition applied to liquidity provision.

n symmetric market makers each choose a quoted depth q_i. Aggregate depth
Q = sum(q_i) determines the effective spread liquidity takers pay via a linear
inverse-demand curve S(Q) = a - b*Q (more total depth -> tighter effective spread).
Each maker bears marginal cost c per unit of depth (capital and adverse-selection
cost of holding/quoting that size) and maximizes profit_i = (S(Q) - c) * q_i.

This is exactly textbook Cournot oligopoly with "spread" standing in for price.
Symmetric equilibrium:
    q*     = (a - c) / (b * (n + 1))
    Q*     = n * q*
    S*     = (a + n*c) / (n + 1)          -> converges to c as n grows (competitive floor)
    profit* = (a - c)^2 / (b * (n + 1)^2)  -> converges to 0 as n grows
"""

import numpy as np


def equilibrium(n, a=1.0, b=1.0, c=0.2):
    q_star = (a - c) / (b * (n + 1))
    Q_star = n * q_star
    S_star = a - b * Q_star
    profit_star = (S_star - c) * q_star
    return q_star, Q_star, S_star, profit_star


def best_response_dynamics(n, a=1.0, b=1.0, c=0.2, n_iter=200, seed=0):
    """
    Verify the closed form is actually reached by iterated best response.

    Uses sequential (Gauss-Seidel) updates: each maker best-responds using the
    latest quantities of the others. Simultaneous (Jacobi) updates, where every
    maker reacts to last round's quantities at once, are only a stable dynamic for
    n <= 2 in this linear-demand setup (the aggregate-quantity recursion has
    factor -(n-1)/2, which leaves the unit circle at n=3); sequential updating is
    the standard fix and converges for any n tested here.
    """
    rng = np.random.default_rng(seed)
    q = rng.uniform(0, (a - c) / b, size=n)
    for _ in range(n_iter):
        for i in range(n):
            others_sum = q.sum() - q[i]
            # best response: maximize (a - b*(qi + others_sum) - c) * qi over qi >= 0
            q[i] = max(0.0, (a - c - b * others_sum) / (2 * b))
    Q = q.sum()
    S = a - b * Q
    profits = (S - c) * q
    return q, Q, S, profits


if __name__ == "__main__":
    a, b, c = 1.0, 1.0, 0.2
    print("n  |  q* (per maker)  |  Q* (total depth)  |  S* (equilibrium spread)  |  profit* (per maker)")
    for n in range(1, 11):
        q_star, Q_star, S_star, profit_star = equilibrium(n, a, b, c)
        q_br, Q_br, S_br, profits_br = best_response_dynamics(n, a, b, c)
        assert abs(Q_star - Q_br) < 1e-6, "best-response dynamics did not converge to closed form"
        print(f"{n:2d} |  {q_star:14.4f}  |  {Q_star:16.4f}  |  {S_star:22.4f}  |  {profit_star:10.5f}")

    print("\nAs n grows, equilibrium spread S* converges toward marginal cost "
          f"c={c} and per-maker profit converges toward 0, both confirmed above.")
