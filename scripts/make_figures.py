"""Build the report figures from real data and the results files.

Run from the repo root, after the analysis scripts:
    PYTHONPATH=. python3 scripts/make_figures.py

Design (dataviz method): palette slots validated with the method's validator on the
light surface (categorical slots 1-3 and the blue ordinal ramp); 2px lines; solid
hairline grid; text in ink tokens, never the series colour; a legend whenever a
chart has two or more series; sparing direct labels; no dual axes; every figure has
a CSV twin in results/figures/data/. Aqua (slot 3) is below 3:1 contrast on the
light surface, so where it is used the values are also labelled and the CSV exists.
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from arch.data import sp500
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from scipy.optimize import brentq

from src import stats_utils as su
from src import vrp

SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
BLUE_400, BLUE_600 = "#3987e5", "#184f95"
LW = 1.6
DPI = 170
FIG = "results/figures"
DATA = os.path.join(FIG, "data")
RNG = np.random.default_rng(11)


def apply_style():
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": AXIS,
            "axes.linewidth": 0.8,
            "axes.labelcolor": INK2,
            "text.color": INK,
            "xtick.color": AXIS,
            "ytick.color": AXIS,
            "xtick.labelcolor": INK2,
            "ytick.labelcolor": INK2,
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.grid": False,
            "grid.color": GRID,
            "grid.linewidth": 0.7,
            "grid.linestyle": "-",
            "legend.frameon": False,
            "legend.fontsize": 8.6,
            "legend.labelcolor": INK2,
            "lines.solid_capstyle": "round",
            "lines.solid_joinstyle": "round",
        }
    )


def base_axes(ax):
    ax.set_axisbelow(True)
    ax.yaxis.grid(True)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=3, width=0.8)


def titles(fig, title, subtitle, source):
    fig.text(0.012, 0.968, title, fontsize=12.2, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.012, 0.915, subtitle, fontsize=8.8, color=INK2, ha="left", va="top", linespacing=1.35)
    fig.text(0.012, 0.012, source, fontsize=7.4, color=MUTED, ha="left", va="bottom")


def line_key(color, label):
    return Line2D([0], [0], color=color, lw=LW, label=label)


def save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print("saved", path)


def fig1_vix_vs_realized():
    df = vrp.add_payoffs(vrp.load_frame(21)).dropna(subset=["vix"])
    s = pd.DataFrame(
        {
            "vix_at_window_start": df["vix"],
            "realized_vol_next_21_days": 100.0 * np.sqrt(df["rv_fwd"]),
        }
    ).dropna()
    gap = s["vix_at_window_start"] - s["realized_vol_next_21_days"]
    share_above, mean_gap = float((gap > 0).mean()), float(gap.mean())
    assert abs(share_above - 0.817) < 0.005 and abs(mean_gap - 3.0) < 0.05, (share_above, mean_gap)
    s.round(3).to_csv(os.path.join(DATA, "fig1_vix_vs_realized.csv"))

    fig, ax = plt.subplots(figsize=(10, 5.5))
    base_axes(ax)
    ax.plot(s.index, s["vix_at_window_start"], color=BLUE, lw=LW)
    ax.plot(s.index, s["realized_vol_next_21_days"], color=ORANGE, lw=LW)
    ax.set_ylim(0, 46)
    ax.set_ylabel("Annualized volatility, % (vol points)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    def mark(lo, hi, label, dx_days, ytext, right_aligned=False):
        seg = s.loc[lo:hi]
        t = (seg["realized_vol_next_21_days"] - seg["vix_at_window_start"]).idxmax()
        y = float(seg.loc[t, "realized_vol_next_21_days"])
        p = float(seg.loc[t, "vix_at_window_start"])
        ax.plot([t], [y], marker="o", ms=6, color=ORANGE, mec=SURFACE, mew=1.6, ls="none", zorder=5)
        ax.annotate(
            f"{label}\nwindow starting {t:%d %b %Y}:\npriced {p:.0f}, delivered {y:.0f}",
            xy=(t, y),
            xytext=(t + pd.Timedelta(days=dx_days), ytext),
            fontsize=8.2,
            color=INK2,
            ha="right" if right_aligned else "left",
            va="center",
            arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.8, "shrinkA": 2, "shrinkB": 4},
        )

    mark("2015-07-15", "2015-08-31", "August 2015 selloff", -45, 38, right_aligned=True)
    mark("2018-01-02", "2018-02-28", "February 2018 volatility shock", -60, 38, right_aligned=True)
    fig.legend(
        handles=[
            line_key(BLUE, "VIX on the first day (what was priced)"),
            line_key(ORANGE, "S&P 500 realized volatility over the next 21 trading days (what was delivered)"),
        ],
        loc="upper left",
        bbox_to_anchor=(0.062, 0.845),
        ncol=1,
    )
    titles(
        fig,
        "Implied volatility sat above delivered volatility most of the time, until it did not",
        f"Real data, 1,236 daily windows starting Jan 2014 to Nov 2018. The VIX was above subsequent realized volatility in {share_above:.0%} of them,\n"
        f"by {mean_gap:.1f} vol points on average. The two spikes are the months that erased the premium.",
        "Source: VIX and S&P 500 daily closes bundled in the arch package. Realized volatility = sqrt(252/21 x sum of squared daily log returns).",
    )
    fig.subplots_adjust(top=0.775, bottom=0.10, left=0.07, right=0.985)
    save(fig, "fig1_vix_vs_realized.png")


def fig2_monthly_payoffs():
    df = vrp.add_payoffs(vrp.load_frame(21)).dropna(subset=["vix"])
    m0 = vrp.nonoverlap(df, 21, 0)["R_var"].dropna()
    vals = m0.values
    sd_ann = m0.std(ddof=1) * np.sqrt(12)
    scale = 0.10 / sd_ann
    r = np.maximum(scale * vals, -1.0)
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))
    mdd = float((np.concatenate([[1.0], eq]) / peak - 1.0).min())
    out = pd.DataFrame({"window_start": m0.index, "payoff_per_unit_strike_variance": vals.round(5), "growth_of_1_at_10pct_vol": eq.round(5)})
    out.to_csv(os.path.join(DATA, "fig2_monthly_payoffs.csv"), index=False)

    fig, (a, b) = plt.subplots(2, 1, figsize=(10, 7.4), sharex=True, gridspec_kw={"height_ratios": [1.15, 1]})
    for ax in (a, b):
        base_axes(ax)
    colors = np.where(vals >= 0, BLUE, RED)
    a.bar(m0.index, vals, width=20, color=colors, linewidth=0)
    a.axhline(0, color=AXIS, lw=0.9)
    a.set_ylabel("Payoff per unit of strike variance\n(premium received = 1.0)")
    a.set_ylim(-5.3, 1.4)
    worst = m0.nsmallest(3)
    for t, v in worst.items():
        left = t > pd.Timestamp("2018-06-01")
        a.annotate(
            f"start {t:%d %b %Y}\n{v:.1f}",
            xy=(t, v),
            xytext=(t + pd.Timedelta(days=-30 if left else 38), v + 0.35),
            fontsize=8.2,
            color=INK2,
            ha="right" if left else "left",
            va="center",
        )
    a.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, fc=BLUE, lw=0, label="Gain (VIX above realized)"),
            plt.Rectangle((0, 0), 1, 1, fc=RED, lw=0, label="Loss (realized above VIX)"),
        ],
        loc="lower left",
        ncol=1,
    )
    x_eq = [m0.index[0]] + [t + pd.Timedelta(days=29) for t in m0.index]
    y_eq = np.concatenate([[1.0], eq])
    b.plot(x_eq, y_eq, color=BLUE, lw=LW)
    b.plot([x_eq[-1]], [y_eq[-1]], marker="o", ms=6, color=BLUE, mec=SURFACE, mew=1.6, ls="none")
    b.set_ylabel("Growth of $1 at a 10%\nvolatility target")
    b.annotate(f"${y_eq[-1]:.2f}", xy=(x_eq[-1], y_eq[-1]), xytext=(8, -2), textcoords="offset points", fontsize=8.6, color=INK2, va="center")
    b.set_ylim(0.8, 1.6)
    b.text(
        0.012,
        0.92,
        f"Worst month {r.min():.0%}, maximum drawdown {mdd:.0%}. Gross of all costs, held to expiry.",
        transform=b.transAxes,
        fontsize=8.4,
        color=INK2,
        va="top",
    )
    b.xaxis.set_major_locator(mdates.YearLocator())
    b.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    b.set_xlim(m0.index[0] - pd.Timedelta(days=25), m0.index[-1] + pd.Timedelta(days=120))
    titles(
        fig,
        "Steady small gains, then occasional losses several times the monthly premium",
        "Real data, 59 non-overlapping 21-day windows, short 30-day variance proxy struck at VIX squared.\n"
        "Top: one bar per window. Bottom: the same payoffs scaled to 10% annualized volatility and compounded.",
        "Source: VIX and S&P 500 daily closes bundled in the arch package. Window grid starts on the first VIX date. No transaction costs or margin.",
    )
    fig.subplots_adjust(top=0.865, bottom=0.075, left=0.09, right=0.97, hspace=0.12)
    save(fig, "fig2_monthly_payoffs.png")


def fig3_cost_sensitivity():
    df = vrp.add_payoffs(vrp.load_frame(21)).dropna(subset=["vix"])
    d = df.dropna(subset=["rv_fwd"])
    grid = np.round(np.arange(0.0, 3.01, 0.1), 2)
    rows = []
    for c in grid:
        rows.append(
            {
                "concession_volpts": c,
                "t_short_variance": su.newey_west_t(vrp.payoff_with_cost(d, c, "var"), 20),
                "t_short_volatility": su.newey_west_t(vrp.payoff_with_cost(d, c, "vol"), 20),
            }
        )
    t = pd.DataFrame(rows)
    t.round(4).to_csv(os.path.join(DATA, "fig3_cost_sensitivity.csv"), index=False)

    be = {k: brentq(lambda c, k=k: vrp.payoff_with_cost(d, c, k).mean(), 0.0, 13.0) for k in ("var", "vol")}

    def cross(col, level=1.96):
        x, y = t["concession_volpts"].values, t[col].values
        for i in range(len(y) - 1):
            if y[i] >= level > y[i + 1]:
                return x[i] + (y[i] - level) / (y[i] - y[i + 1]) * (x[i + 1] - x[i])
        return float("nan")

    c_var, c_vol = cross("t_short_variance"), cross("t_short_volatility")
    fig, ax = plt.subplots(figsize=(10, 5.2))
    base_axes(ax)
    ax.axhline(1.96, color=AXIS, lw=0.9)
    ax.text(3.02, 1.96, "t = 1.96", fontsize=8.2, color=MUTED, va="center", ha="left")
    ax.axhline(0, color=AXIS, lw=0.9)
    ax.plot(t["concession_volpts"], t["t_short_variance"], color=BLUE, lw=LW)
    ax.plot(t["concession_volpts"], t["t_short_volatility"], color=ORANGE, lw=LW)
    for xv, col in ((be["var"], BLUE), (be["vol"], ORANGE)):
        ax.plot([xv], [0], marker="o", ms=6, color=col, mec=SURFACE, mew=1.6, ls="none", zorder=5)
    ax.set_xlim(0, 3.0)
    ax.set_xlabel("Selling concession below the VIX, in volatility points (a stylized stand-in for bid-ask and hedging costs)")
    ax.set_ylabel("Newey-West t-statistic of the mean payoff")
    ax.legend(
        handles=[
            line_key(BLUE, f"Short variance proxy: below t = 1.96 after {c_var:.1f} vol points, mean payoff zero at {be['var']:.1f}"),
            line_key(ORANGE, f"Short volatility proxy: below t = 1.96 after {c_vol:.1f} vol points, mean payoff zero at {be['vol']:.1f}"),
        ],
        loc="upper right",
    )
    titles(
        fig,
        f"A selling concession of {c_var:.1f} to {c_vol:.1f} vol points removes the statistical significance of the premium",
        "Real data, 1,236 daily windows 2014-2018 (HAC with 20 lags). The position is sold at (VIX minus c) instead of the VIX mid.\n"
        "The gross premium in this sample is 3.0 vol points. Markers show where the mean payoff reaches zero.",
        "Source: VIX and S&P 500 daily closes bundled in the arch package. The concession is illustrative, not a measured spread.",
    )
    fig.subplots_adjust(top=0.84, bottom=0.14, left=0.07, right=0.945)
    save(fig, "fig3_cost_sensitivity.png")


def fig4_rolling_verifiability():
    tab = pd.read_csv("results/rolling_premium_verifiability.csv")
    names = {"Mkt-RF": "Market (Mkt-RF)", "HML": "Value (HML)", "SMB": "Size (SMB)"}
    cols = {"Mkt-RF": BLUE, "HML": ORANGE, "SMB": AQUA}
    tab.round(4).to_csv(os.path.join(DATA, "fig4_rolling_verifiability.csv"), index=False)
    fig, ax = plt.subplots(figsize=(10, 5.2))
    base_axes(ax)
    ax.axhline(0.8, color=AXIS, lw=0.9)
    ax.text(30.6, 0.8, "80%", fontsize=8.2, color=MUTED, va="center", ha="left")
    handles = []
    for key in ("Mkt-RF", "HML", "SMB"):
        sub = tab[tab["series"] == key]
        ax.plot(sub["window_years"], sub["share_t_above_1.96"], color=cols[key], lw=LW, marker="o", ms=6, mec=SURFACE, mew=1.6)
        handles.append(line_key(cols[key], names[key]))
        five = sub[sub["window_years"] == 5].iloc[0]["share_t_above_1.96"]
        off = {"Mkt-RF": (7, 7), "HML": (9, 7), "SMB": (8, -15)}[key]
        ax.annotate(f"{five:.0%}", xy=(5, five), xytext=off, textcoords="offset points", fontsize=8.6, color=INK2)
    ax.set_xticks([3, 5, 10, 20, 30])
    ax.set_xlim(2, 32.2)
    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel("Length of the rolling window, years")
    ax.set_ylabel("Share of windows where the mean\nreturn has t above 1.96")
    ax.legend(handles=handles, loc="upper left")
    titles(
        fig,
        "Even premia with 90 years of history are usually not verifiable in a 5-year window",
        "Real data: Fama-French monthly factors, Jul 1926 to Nov 2018 (full-sample Sharpe 0.43 market, 0.37 value, 0.22 size).\n"
        "Each point is the share of overlapping rolling windows in which a plain t-test would have 'verified' the premium.",
        "Source: Fama-French monthly factors bundled in the arch package. Overlapping windows, so points are not independent.",
    )
    fig.subplots_adjust(top=0.84, bottom=0.14, left=0.085, right=0.97)
    save(fig, "fig4_rolling_verifiability.png")


def fig5_power_curves():
    df = vrp.add_payoffs(vrp.load_frame(21)).dropna(subset=["vix"])
    shape = vrp.nonoverlap(df, 21, 0)["R_var"].dropna().values
    st = su.describe(shape, 12)
    years = [1, 2, 3, 4, 5, 7, 10, 15, 20, 25, 30]
    levels = [(0.0, MUTED, "True Sharpe 0 (no edge): false-positive rate"), (0.5, BLUE_400, "True Sharpe 0.5"), (1.0, BLUE_600, "True Sharpe 1.0")]
    rows = []
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 5.0), sharey=True)
    for ax, kind, ttl in (
        (axes[0], "normal", "Normal returns"),
        (axes[1], "empirical", f"Short-volatility shape (skew {st['skew']:.1f}, kurtosis {st['kurtosis']:.0f})"),
    ):
        base_axes(ax)
        ax.axhline(0.05, color=AXIS, lw=0.9)
        for sr, col, _ in levels:
            ys = []
            for y in years:
                p = su.power_normal(sr, y) if kind == "normal" else su.power_empirical_shape(shape, sr, y, RNG, reps=4000)
                ys.append(p)
                rows.append({"shape": kind, "true_sharpe": sr, "years": y, "prob_t_above_1.645": p})
            ax.plot(years, ys, color=col, lw=LW)
            ax.annotate(f"{sr:g}", xy=(30, ys[-1]), xytext=(6, 0), textcoords="offset points", fontsize=8.4, color=INK2, va="center")
        ax.set_title(ttl, fontsize=9.6, color=INK, loc="left", pad=8)
        ax.set_xlim(0, 32.5)
        ax.set_ylim(0, 1.02)
        ax.set_xticks([1, 5, 10, 20, 30])
        ax.set_xlabel("Years of monthly data")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    axes[0].set_ylabel("Probability that a one-sided t-test\nshows t above 1.645")
    axes[0].text(0.6, 0.065, "5% nominal", fontsize=8.0, color=MUTED, va="bottom")
    axes[1].legend(handles=[line_key(c, lab) for _, c, lab in levels], loc="center right", bbox_to_anchor=(1.0, 0.36))
    pd.DataFrame(rows).round(4).to_csv(os.path.join(DATA, "fig5_power_curves.csv"), index=False)
    titles(
        fig,
        "No-edge, short-volatility-shaped returns look verified 2 to 3 times too often in 3 to 5 years",
        "HYPOTHETICAL power analysis, not a performance claim. Monthly returns are normal (left) or resampled from the real 2014-2018\n"
        "short-variance payoffs, standardized, then shifted to the stated true Sharpe ratio (right). 4,000 resamples per point.",
        "Source: src/stats_utils.py on the real payoff shape. The right-hand shape comes from only 59 observations, so its tails are probably too light.",
    )
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.085, right=0.97, wspace=0.08)
    save(fig, "fig5_power_curves.png")


def fig6_realized_vol_context():
    spx = sp500.load()["Close"]
    r = np.log(spx).diff()
    rv = 100.0 * np.sqrt((252.0 / 21) * (r ** 2).rolling(21).sum())
    rv = rv.dropna()
    rv.round(3).rename("realized_vol_trailing_21d").to_csv(os.path.join(DATA, "fig6_realized_vol_context.csv"))
    blocks = pd.Series({y: rv.loc[f"{y}-01-01":f"{y + 4}-12-31"].mean() for y in range(1999, 2015)}).sort_values()
    rank = list(blocks.index).index(2014) + 1
    mean_all, mean_sub = float(rv.mean()), float(rv.loc["2014-01-01":"2018-12-31"].mean())
    fig, ax = plt.subplots(figsize=(10, 5.0))
    base_axes(ax)
    ax.axvspan(pd.Timestamp("2014-01-03"), pd.Timestamp("2018-12-31"), color=GRID, alpha=0.7, lw=0)
    ax.axhline(40, color=AXIS, lw=0.9)
    ax.plot(rv.index, rv.values, color=BLUE, lw=LW)
    ax.set_ylim(0, 95)
    ax.set_ylabel("S&P 500 realized volatility over the\nprevious 21 trading days, % per year")
    ax.text(pd.Timestamp("2014-04-01"), 88, "Window used for the\npremium tests (VIX data)", fontsize=8.4, color=INK2, va="top")
    ax.text(pd.Timestamp("1999-03-01"), 41.5, "40", fontsize=8.2, color=MUTED, va="bottom")
    for lo, hi, lab, dx in (
        ("2002-06-01", "2002-12-31", "2002", -40),
        ("2008-09-01", "2009-01-31", "2008", -230),
        ("2009-02-01", "2009-06-30", "2009", 40),
        ("2011-07-01", "2011-10-31", "2011", 40),
    ):
        seg = rv.loc[lo:hi]
        tpk = seg.idxmax()
        ax.annotate(
            f"{lab}: {seg.max():.0f}",
            xy=(tpk, seg.max()),
            xytext=(tpk + pd.Timedelta(days=dx), seg.max() + 4),
            fontsize=8.4,
            color=INK2,
            ha="left",
        )
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    titles(
        fig,
        f"The five-year window behind the premium tests is one of the calmest in the record (rank {rank} of 16)",
        f"Real data, S&P 500 daily closes 1999-2018. Mean realized volatility is {mean_sub:.1f} in the shaded years against {mean_all:.1f} over all 20 years.\n"
        "None of the episodes above 40 (2002, 2008, 2009, 2011) fell inside the window, so a record built only on the shaded years never faced one.",
        "Source: S&P 500 daily closes bundled in the arch package.",
    )
    fig.subplots_adjust(top=0.82, bottom=0.11, left=0.085, right=0.985)
    save(fig, "fig6_realized_vol_context.png")


def main():
    os.makedirs(DATA, exist_ok=True)
    apply_style()
    fig1_vix_vs_realized()
    fig2_monthly_payoffs()
    fig3_cost_sensitivity()
    fig4_rolling_verifiability()
    fig5_power_curves()
    fig6_realized_vol_context()


if __name__ == "__main__":
    main()
