"""
Repeated Prisoner's Dilemma: round-robin tournament of classic strategies, plus a
direct numerical check of the folk-theorem discount-factor threshold for whether
tacit collusion (cooperation) is sustainable.

Stage game payoffs (row player, col player), C = cooperate/collude, D = defect:
            C        D
    C     (3,3)    (0,5)
    D     (5,0)    (1,1)
T=5 (temptation), R=3 (reward), P=1 (punishment), S=0 (sucker).
"""

import itertools

import numpy as np

PAYOFF = {("C", "C"): (3, 3), ("C", "D"): (0, 5), ("D", "C"): (5, 0), ("D", "D"): (1, 1)}


def always_cooperate(my_hist, opp_hist):
    return "C"


def always_defect(my_hist, opp_hist):
    return "D"


def tit_for_tat(my_hist, opp_hist):
    return "C" if not opp_hist else opp_hist[-1]


def grim_trigger(my_hist, opp_hist):
    return "D" if "D" in opp_hist else "C"


def pavlov(my_hist, opp_hist):
    """Win-stay-lose-shift: repeat last move if it scored well, else switch."""
    if not my_hist:
        return "C"
    last_payoff = PAYOFF[(my_hist[-1], opp_hist[-1])][0]
    won = last_payoff >= 3
    if won:
        return my_hist[-1]
    return "D" if my_hist[-1] == "C" else "C"


STRATEGIES = {
    "always_cooperate": always_cooperate,
    "always_defect": always_defect,
    "tit_for_tat": tit_for_tat,
    "grim_trigger": grim_trigger,
    "pavlov": pavlov,
}


def play_match(strat_a, strat_b, n_rounds):
    hist_a, hist_b = [], []
    total_a = total_b = 0.0
    for _ in range(n_rounds):
        move_a = strat_a(hist_a, hist_b)
        move_b = strat_b(hist_b, hist_a)
        pa, pb = PAYOFF[(move_a, move_b)]
        total_a += pa
        total_b += pb
        hist_a.append(move_a)
        hist_b.append(move_b)
    return total_a / n_rounds, total_b / n_rounds


def round_robin_tournament(n_rounds=150):
    names = list(STRATEGIES)
    scores = {name: 0.0 for name in names}
    matches = 0
    for a, b in itertools.combinations_with_replacement(names, 2):
        avg_a, avg_b = play_match(STRATEGIES[a], STRATEGIES[b], n_rounds)
        scores[a] += avg_a
        scores[b] += avg_b
        matches += 1
    return scores


def discounted_payoff_grim_self_play(w, n_rounds=2000):
    """Discounted total payoff of grim-trigger vs grim-trigger (perpetual cooperation)."""
    weights = w ** np.arange(n_rounds)
    return 3.0 * weights.sum()


def discounted_payoff_one_shot_deviation(w, n_rounds=2000):
    """
    Defect once against grim trigger, then get punished (mutual defection) forever
    after. Temptation payoff T in round 0, punishment payoff P in every round after.
    """
    weights = w ** np.arange(n_rounds)
    return 5.0 * weights[0] + 1.0 * weights[1:].sum()


if __name__ == "__main__":
    print("=== Round-robin tournament (150 rounds/match, avg payoff per round) ===")
    scores = round_robin_tournament()
    for name, score in sorted(scores.items(), key=lambda kv: -kv[1]):
        print(f"{name:18s} total score={score:.2f}")

    print("\n=== Folk theorem: discount factor threshold for sustaining cooperation ===")
    print("Grim trigger sustains cooperation iff discounted defect payoff <= discounted "
          "cooperate payoff, theoretical threshold w* = (T-R)/(T-P) = (5-3)/(5-1) = 0.5")
    for w in [0.3, 0.4, 0.5, 0.6, 0.7]:
        coop = discounted_payoff_grim_self_play(w)
        defect = discounted_payoff_one_shot_deviation(w)
        better = "cooperate" if coop >= defect else "defect"
        print(f"w={w:.2f}: discounted cooperate payoff={coop:.3f}, "
              f"discounted deviate-then-punished payoff={defect:.3f} -> {better} is better")
