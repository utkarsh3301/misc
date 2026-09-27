"""
Glosten-Milgrom (1985) sequential trade model.

True value V is V_H with prior probability p0, else V_L. A fraction `alpha` of
arriving traders are informed (know V exactly and trade accordingly); the rest are
uninformed and buy or sell with probability 1/2 regardless of V. A competitive,
risk-neutral market maker cannot tell informed from uninformed apart, so it sets
bid/ask using Bayes' rule so that it breaks even in expectation conditional on
each side being hit:

  ask = E[V | a buy arrives]
  bid = E[V | a sell arrives]

The spread (ask - bid) is pure compensation for adverse selection: with alpha = 0
(no informed traders) the spread collapses to zero, with alpha = 1 it equals the
full V_H - V_L.
"""

import numpy as np


def quotes(p0, v_high, v_low, alpha):
    """Single-round bid/ask given prior p0 = P(V = v_high)."""
    p_buy_given_high = alpha * 1.0 + (1 - alpha) * 0.5
    p_buy_given_low = alpha * 0.0 + (1 - alpha) * 0.5
    p_sell_given_high = alpha * 0.0 + (1 - alpha) * 0.5
    p_sell_given_low = alpha * 1.0 + (1 - alpha) * 0.5

    p_buy = p0 * p_buy_given_high + (1 - p0) * p_buy_given_low
    p_sell = p0 * p_sell_given_high + (1 - p0) * p_sell_given_low

    ask = (p0 * p_buy_given_high * v_high + (1 - p0) * p_buy_given_low * v_low) / p_buy
    bid = (p0 * p_sell_given_high * v_high + (1 - p0) * p_sell_given_low * v_low) / p_sell
    return bid, ask


def spread_curve(alphas, p0=0.5, v_high=110.0, v_low=90.0):
    return np.array([quotes(p0, v_high, v_low, a)[1] - quotes(p0, v_high, v_low, a)[0]
                      for a in alphas])


def simulate_belief_path(true_value, v_high, v_low, alpha, n_trades, p0=0.5, seed=0):
    """
    Chain single-round updating across a sequence of trades: after each trade,
    the posterior P(V = v_high) becomes the new prior for the next quote. Returns
    the belief path and the bid/ask path, showing price discovery speed.
    """
    rng = np.random.default_rng(seed)
    belief = p0
    beliefs = [belief]
    bids, asks = [], []

    for _ in range(n_trades):
        bid, ask = quotes(belief, v_high, v_low, alpha)
        bids.append(bid)
        asks.append(ask)

        is_informed = rng.random() < alpha
        if is_informed:
            side = "buy" if true_value == v_high else "sell"
        else:
            side = "buy" if rng.random() < 0.5 else "sell"

        # Bayesian update of belief given the observed order side.
        p_buy_given_high = alpha * 1.0 + (1 - alpha) * 0.5
        p_buy_given_low = (1 - alpha) * 0.5
        p_sell_given_high = (1 - alpha) * 0.5
        p_sell_given_low = alpha * 1.0 + (1 - alpha) * 0.5

        if side == "buy":
            num = belief * p_buy_given_high
            den = belief * p_buy_given_high + (1 - belief) * p_buy_given_low
        else:
            num = belief * p_sell_given_high
            den = belief * p_sell_given_high + (1 - belief) * p_sell_given_low
        belief = num / den
        beliefs.append(belief)

    return np.array(beliefs), np.array(bids), np.array(asks)


if __name__ == "__main__":
    print("=== Spread vs fraction of informed traders (alpha) ===")
    for alpha in [0.0, 0.1, 0.3, 0.5, 0.8, 1.0]:
        bid, ask = quotes(p0=0.5, v_high=110, v_low=90, alpha=alpha)
        print(f"alpha={alpha:.1f}: bid={bid:.2f}, ask={ask:.2f}, spread={ask-bid:.2f}")

    print("\n=== Belief convergence to true value over a sequence of trades ===")
    for alpha in [0.1, 0.3, 0.6]:
        beliefs, bids, asks = simulate_belief_path(
            true_value=110, v_high=110, v_low=90, alpha=alpha, n_trades=50, seed=1
        )
        print(f"alpha={alpha}: belief after 5 trades={beliefs[5]:.3f}, "
              f"after 20 trades={beliefs[20]:.3f}, after 50 trades={beliefs[50]:.3f} "
              f"(true value corresponds to belief -> 1.0)")
