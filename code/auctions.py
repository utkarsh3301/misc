"""
First-price sealed-bid vs second-price (Vickrey) sealed-bid auctions,
independent private values ~ Uniform(0, 1), n risk-neutral bidders.

Second-price: bidding your true value b_i = v_i is a dominant strategy.
First-price:  symmetric equilibrium bid function is b(v) = v * (n-1)/n
              (bidders shade below value to leave a margin, more shading
              the fewer competitors there are).

Revenue equivalence theorem: despite very different individual bidding
behavior, both mechanisms give the same expected seller revenue,
E[revenue] = (n-1)/(n+1), the expected second-highest of n Uniform(0,1) draws.
"""

import numpy as np


def first_price_equilibrium_bid(values, n):
    return values * (n - 1) / n


def run_auctions(n, n_auctions=1_000_000, seed=0):
    rng = np.random.default_rng(seed)
    values = rng.uniform(0.0, 1.0, size=(n_auctions, n))
    sorted_values = np.sort(values, axis=1)
    highest = sorted_values[:, -1]
    second_highest = sorted_values[:, -2] if n > 1 else np.zeros(n_auctions)

    second_price_revenue = second_highest  # winner pays the second-highest value
    first_price_bids = first_price_equilibrium_bid(values, n)
    first_price_revenue = first_price_bids.max(axis=1)  # winner pays their own (shaded) bid

    return second_price_revenue, first_price_revenue


def check_dominant_strategy_second_price(my_value=0.6, n_opponents=4, n_trials=500_000, seed=0):
    """
    Fix a bidder's value and vary their OWN bid away from truthful, holding
    opponents' (truthful) bidding fixed, to confirm truthful bidding maximizes
    the bidder's expected payoff, i.e. is a best response regardless of the
    specific realization of opponents (the defining property of a dominant
    strategy, checked here against the empirical opponent distribution).
    """
    rng = np.random.default_rng(seed)
    opponents = rng.uniform(0.0, 1.0, size=(n_trials, n_opponents))
    opponent_max = opponents.max(axis=1)

    results = {}
    for bid in [my_value - 0.2, my_value - 0.1, my_value, my_value + 0.1, my_value + 0.2]:
        bid = np.clip(bid, 0, 1)
        wins = bid > opponent_max
        payoff = np.where(wins, my_value - opponent_max, 0.0)
        results[round(bid, 2)] = payoff.mean()
    return results


if __name__ == "__main__":
    print("=== Revenue equivalence: first-price vs second-price ===")
    for n in [2, 3, 5, 10]:
        second_rev, first_rev = run_auctions(n)
        theory = (n - 1) / (n + 1)
        print(f"n={n:2d} bidders: theory E[revenue]={theory:.4f}  "
              f"second-price mean={second_rev.mean():.4f} (std={second_rev.std():.4f})  "
              f"first-price mean={first_rev.mean():.4f} (std={first_rev.std():.4f})")

    print("\n=== Second-price truthfulness is a dominant strategy (value=0.6, 4 opponents) ===")
    results = check_dominant_strategy_second_price()
    for bid, payoff in results.items():
        marker = "  <- truthful" if abs(bid - 0.6) < 1e-9 else ""
        print(f"bid={bid:.2f}: expected payoff={payoff:.5f}{marker}")
