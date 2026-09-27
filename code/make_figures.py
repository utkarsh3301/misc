"""
Generate the figures used alongside quant-trading-models.md from the model
scripts in this directory. Static PNGs saved to ../figures/.

Colors are the validated default categorical palette (light mode, slots 1-3:
blue/orange/aqua) from the dataviz skill's reference palette, used in fixed
order rather than an arbitrary matplotlib cycle.

Run: python3 code/make_figures.py
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import auctions
import cournot_market_makers as cournot
import glosten_milgrom as gm
import iterated_prisoners_dilemma as ipd
import kyle_model

FIG_DIR = os.path.join(os.path.dirname(__file__), "..", "figures")

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"


def style_axis(ax, title, xlabel, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, color=INK_PRIMARY, fontsize=12, loc="left", pad=10)
    ax.set_xlabel(xlabel, color=INK_SECONDARY, fontsize=10)
    ax.set_ylabel(ylabel, color=INK_SECONDARY, fontsize=10)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(BASELINE)
    ax.grid(True, axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def save(fig, name):
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def fig_glosten_milgrom_spread():
    alphas = np.linspace(0, 1, 100)
    spreads = gm.spread_curve(alphas, p0=0.5, v_high=110, v_low=90)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(alphas, spreads, color=BLUE, linewidth=2.5)
    style_axis(ax, "Bid-ask spread widens with the fraction of informed traders",
               "alpha (fraction of informed traders)", "spread")
    save(fig, "glosten_milgrom_spread.png")


def fig_glosten_milgrom_belief():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for color, alpha in zip([BLUE, ORANGE, AQUA], [0.1, 0.3, 0.6]):
        beliefs, _, _ = gm.simulate_belief_path(
            true_value=110, v_high=110, v_low=90, alpha=alpha, n_trades=50, seed=1
        )
        ax.plot(beliefs, color=color, linewidth=2.2, label=f"alpha = {alpha}")
    ax.axhline(1.0, color=BASELINE, linewidth=1, linestyle="--")
    style_axis(ax, "Higher informed-trader share speeds up price discovery",
               "trade number", "market belief that V = V_high")
    ax.legend(frameon=False, labelcolor=INK_SECONDARY, fontsize=9)
    save(fig, "glosten_milgrom_belief_convergence.png")


def fig_cournot():
    ns = np.arange(1, 11)
    a, b, c = 1.0, 1.0, 0.2
    spreads = [cournot.equilibrium(n, a, b, c)[2] for n in ns]
    profits = [cournot.equilibrium(n, a, b, c)[3] for n in ns]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    axes[0].plot(ns, spreads, color=BLUE, marker="o", markersize=5, linewidth=2.2)
    axes[0].axhline(c, color=BASELINE, linewidth=1, linestyle="--")
    style_axis(axes[0], "Spread compresses toward marginal cost",
               "competing market makers (n)", "equilibrium spread S*")

    axes[1].plot(ns, profits, color=ORANGE, marker="o", markersize=5, linewidth=2.2)
    style_axis(axes[1], "Per-maker profit is competed away",
               "competing market makers (n)", "equilibrium profit per maker")
    fig.tight_layout()
    save(fig, "cournot_spread_and_profit.png")


def fig_auction_revenue():
    second_rev, first_rev = auctions.run_auctions(n=5, n_auctions=200_000)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bins = np.linspace(0, 1, 60)
    ax.hist(second_rev, bins=bins, color=BLUE, alpha=0.55, label="second-price revenue", density=True)
    ax.hist(first_rev, bins=bins, color=ORANGE, alpha=0.55, label="first-price revenue", density=True)
    ax.axvline(second_rev.mean(), color=BLUE, linewidth=1.5, linestyle="--")
    ax.axvline(first_rev.mean(), color=ORANGE, linewidth=1.5, linestyle="--")
    style_axis(ax, "Same expected revenue, different distributions (n=5 bidders)",
               "seller revenue", "density")
    ax.legend(frameon=False, labelcolor=INK_SECONDARY, fontsize=9)
    save(fig, "auction_revenue_distribution.png")


def fig_kyle_lambda():
    sigma_u_grid = np.linspace(0.2, 5.0, 100)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for color, sigma_v in zip([BLUE, ORANGE, AQUA], [0.5, 1.0, 2.0]):
        lambdas = [kyle_model.kyle_equilibrium(sigma_v, su)[0] for su in sigma_u_grid]
        ax.plot(sigma_u_grid, lambdas, color=color, linewidth=2.2, label=f"sigma_v = {sigma_v}")
    style_axis(ax, "Price impact falls as noise-trader volume rises",
               "sigma_u (noise trader order flow std dev)", "lambda (price impact per unit flow)")
    ax.legend(frameon=False, labelcolor=INK_SECONDARY, fontsize=9)
    save(fig, "kyle_price_impact.png")


def fig_ipd_threshold():
    ws = np.linspace(0.1, 0.9, 100)
    coop = [ipd.discounted_payoff_grim_self_play(w) for w in ws]
    defect = [ipd.discounted_payoff_one_shot_deviation(w) for w in ws]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(ws, coop, color=BLUE, linewidth=2.2, label="stay cooperative (grim trigger)")
    ax.plot(ws, defect, color=ORANGE, linewidth=2.2, label="defect once, then punished forever")
    ax.axvline(0.5, color=BASELINE, linewidth=1, linestyle="--")
    style_axis(ax, "Cooperation pays once w crosses the folk-theorem threshold",
               "discount factor / probability of continued play (w)", "discounted payoff")
    ax.legend(frameon=False, labelcolor=INK_SECONDARY, fontsize=9)
    save(fig, "ipd_discount_threshold.png")


if __name__ == "__main__":
    os.makedirs(FIG_DIR, exist_ok=True)
    fig_glosten_milgrom_spread()
    fig_glosten_milgrom_belief()
    fig_cournot()
    fig_auction_revenue()
    fig_kyle_lambda()
    fig_ipd_threshold()
