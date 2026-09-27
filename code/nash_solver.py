"""
Nash equilibrium (2-player normal form, via support enumeration) and Shapley value.

Nash: given payoff matrices A (row player, m x n) and B (column player, m x n),
find all (x, y) equilibria by enumerating candidate supports of equal size and
solving the indifference conditions, then checking best-response conditions.
This is exact for small games and covers pure equilibria as the size-1 case.

Shapley value: fair allocation of a coalition's total value across players, by
each player's average marginal contribution over all orderings.
"""

import itertools
import math

import numpy as np

TOL = 1e-8


def _solve_mixed_given_support(payoff_for_opponent_indiff, support, other_support):
    """
    Solve for a mixed strategy over `support` that makes the OPPONENT indifferent
    among `other_support`, using `payoff_for_opponent_indiff` = the opponent's
    payoff matrix (rows = this player's actions, cols = opponent's actions).

    Returns a probability vector over the full action set (zeros outside support),
    or None if no valid solution exists.
    """
    k = len(support)
    n_actions = payoff_for_opponent_indiff.shape[0]
    # Build k equations: k-1 indifference equations + 1 normalization.
    sub = payoff_for_opponent_indiff[list(support), :][:, list(other_support)]  # k x k
    if sub.shape[0] != sub.shape[1]:
        return None
    A_eq = np.zeros((k, k))
    b_eq = np.zeros(k)
    for row in range(k - 1):
        A_eq[row, :] = sub[:, row] - sub[:, row + 1]
        b_eq[row] = 0.0
    A_eq[k - 1, :] = 1.0
    b_eq[k - 1] = 1.0
    try:
        probs = np.linalg.solve(A_eq, b_eq)
    except np.linalg.LinAlgError:
        return None
    if np.any(probs < -TOL):
        return None
    probs = np.clip(probs, 0, None)
    full = np.zeros(n_actions)
    for idx, action in enumerate(support):
        full[action] = probs[idx]
    return full


def find_nash_equilibria(A, B):
    """
    Enumerate all Nash equilibria of a 2-player bimatrix game (A, B), each m x n,
    via support enumeration. Returns a list of (x, y, value_row, value_col).
    """
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    m, n = A.shape
    equilibria = []
    seen = set()

    for k in range(1, min(m, n) + 1):
        for row_support in itertools.combinations(range(m), k):
            for col_support in itertools.combinations(range(n), k):
                # y (column player's mix) makes ROW player indifferent among row_support:
                # uses A restricted to (row_support, col_support).
                y_full = _solve_mixed_given_support(A, col_support, row_support)
                # x (row player's mix) makes COLUMN player indifferent among col_support:
                # uses B^T restricted the same way.
                x_full = _solve_mixed_given_support(B.T, row_support, col_support)
                if y_full is None or x_full is None:
                    continue
                if np.any(x_full[list(row_support)] <= TOL) or np.any(y_full[list(col_support)] <= TOL):
                    continue

                row_payoffs = A @ y_full
                col_payoffs = x_full @ B
                v_row = row_payoffs[row_support[0]]
                v_col = col_payoffs[col_support[0]]
                if np.max(row_payoffs) > v_row + TOL:
                    continue
                if np.max(col_payoffs) > v_col + TOL:
                    continue

                key = (tuple(np.round(x_full, 6)), tuple(np.round(y_full, 6)))
                if key in seen:
                    continue
                seen.add(key)
                equilibria.append((x_full, y_full, v_row, v_col))
    return equilibria


def shapley_value(players, characteristic_function):
    """
    players: sequence of hashable player labels.
    characteristic_function: dict mapping frozenset(subset) -> value.
        Must include frozenset() -> 0 (or it is assumed to be 0).
    Returns dict player -> Shapley value.
    """
    n = len(players)
    fact = math.factorial
    values = {p: 0.0 for p in players}

    def v(subset):
        return characteristic_function.get(frozenset(subset), 0.0)

    for i in players:
        others = [p for p in players if p != i]
        total = 0.0
        for r in range(len(others) + 1):
            for subset in itertools.combinations(others, r):
                weight = fact(r) * fact(n - r - 1) / fact(n)
                marginal = v(set(subset) | {i}) - v(set(subset))
                total += weight * marginal
        values[i] = total
    return values


if __name__ == "__main__":
    print("=== Prisoner's Dilemma ===")
    # rows/cols: 0 = Cooperate, 1 = Defect
    A_pd = [[3, 0], [5, 1]]
    B_pd = [[3, 5], [0, 1]]
    for x, y, vr, vc in find_nash_equilibria(A_pd, B_pd):
        print(f"row mix={x}, col mix={y}, row value={vr:.3f}, col value={vc:.3f}")

    print("\n=== Matching Pennies (zero-sum, no pure equilibrium) ===")
    A_mp = [[1, -1], [-1, 1]]
    B_mp = [[-1, 1], [1, -1]]
    for x, y, vr, vc in find_nash_equilibria(A_mp, B_mp):
        print(f"row mix={x}, col mix={y}, row value={vr:.3f}, col value={vc:.3f}")

    print("\n=== Battle of the Sexes (two coordination equilibria) ===")
    A_bos = [[2, 0], [0, 1]]
    B_bos = [[1, 0], [0, 2]]
    for x, y, vr, vc in find_nash_equilibria(A_bos, B_bos):
        print(f"row mix={x}, col mix={y}, row value={vr:.3f}, col value={vc:.3f}")

    print("\n=== Shapley value: 3-strategy trading book ===")
    # Standalone Sharpe-scaled contribution for each strategy, and superadditive
    # value from diversification when combined (correlation < 1 across strategies).
    players = ["momentum", "mean_reversion", "market_making"]
    char_func = {
        frozenset(): 0.0,
        frozenset({"momentum"}): 4.0,
        frozenset({"mean_reversion"}): 3.0,
        frozenset({"market_making"}): 5.0,
        frozenset({"momentum", "mean_reversion"}): 8.5,
        frozenset({"momentum", "market_making"}): 10.5,
        frozenset({"mean_reversion", "market_making"}): 9.5,
        frozenset({"momentum", "mean_reversion", "market_making"}): 16.0,
    }
    sv = shapley_value(players, char_func)
    total = sum(sv.values())
    for p in players:
        print(f"{p}: standalone={char_func[frozenset({p})]:.2f}, shapley={sv[p]:.3f}")
    print(f"sum of shapley values = {total:.3f} (should equal grand coalition value = "
          f"{char_func[frozenset(players)]:.3f})")
