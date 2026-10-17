"""
Small helpers shared by the experiment scripts: saving tables, writing
markdown, and a consistent figure style.
"""

import os

import numpy as np

from .data import ROOT

TABLES = os.path.join(ROOT, "results", "tables")
FIGURES = os.path.join(ROOT, "results", "figures")

# Columns rendered as percentages: exact names plus any name containing
# one of these fragments (cagr, oos_max_dd, median_win_rate, ...).
PCT_COLS = {"vol", "total_return", "avg_win", "avg_loss"}
PCT_FRAGMENTS = ("cagr", "max_dd", "win_rate", "exposure", "hit_rate", "_pct", "beats", "share")


def save_table(df, name):
    os.makedirs(TABLES, exist_ok=True)
    path = os.path.join(TABLES, f"{name}.csv")
    df.to_csv(path, index=False, float_format="%.6g")
    return path


def fig_path(name):
    os.makedirs(FIGURES, exist_ok=True)
    return os.path.join(FIGURES, f"{name}.png")


def _fmt(col, v):
    if isinstance(v, (float, np.floating)):
        if not np.isfinite(v):
            return "inf" if v == np.inf else "n/a"
        if col in PCT_COLS or any(f in col for f in PCT_FRAGMENTS):
            return f"{v * 100:.1f}%"
        if col.endswith("_bps"):
            return f"{v:.1f}"
        if abs(v) >= 100:
            return f"{v:.0f}"
        return f"{v:.2f}"
    return str(v)


def markdown(df, cols=None, rename=None):
    """Render a DataFrame as a GitHub markdown table with sensible number formats."""
    cols = cols or list(df.columns)
    head = [rename.get(c, c) if rename else c for c in cols]
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in df[cols].iterrows():
        lines.append("| " + " | ".join(_fmt(c, row[c]) for c in cols) + " |")
    return "\n".join(lines)


# Validated categorical order (dataviz reference palette, light mode).
# Always assigned in this order, never cycled.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781",
       "grid": "#e1e0d9", "axis": "#c3c2b7", "surface": "#fcfcfb"}
DIVERGING = ["#184f95", "#3987e5", "#9ec5f4", "#f0efec", "#f4a3a2", "#e34948", "#a32a2a"]


def label_line_ends(ax, items, min_gap=0.035, log=True):
    """
    Direct labels at the right end of each line, nudged apart so they never
    overlap. items: list of (label, x_last, y_last). min_gap is in axis
    fraction units.
    """
    import matplotlib.transforms as mtrans
    lo, hi = ax.get_ylim()
    to_frac = (lambda y: (np.log10(y) - np.log10(lo)) / (np.log10(hi) - np.log10(lo))) if log else \
        (lambda y: (y - lo) / (hi - lo))
    placed = sorted(((to_frac(y), lab, x) for lab, x, y in items), key=lambda t: t[0])
    ys = [p[0] for p in placed]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + min_gap)
    shift = max(0.0, ys[-1] - 0.98) if ys else 0.0
    ys = [y - shift for y in ys]
    trans = mtrans.blended_transform_factory(ax.transData, ax.transAxes)
    for (frac, lab, x), y in zip(placed, ys):
        ax.text(x, y, "  " + lab, transform=trans, fontsize=8, color=INK["secondary"], va="center")


def diverging_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("blue_gray_red", DIVERGING[::-1])


def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from cycler import cycler
    plt.rcParams.update({
        "figure.dpi": 120, "savefig.dpi": 120, "savefig.bbox": "tight",
        "figure.facecolor": INK["surface"], "axes.facecolor": INK["surface"],
        "savefig.facecolor": INK["surface"],
        "axes.prop_cycle": cycler(color=SERIES),
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": INK["axis"], "axes.labelcolor": INK["secondary"],
        "axes.titlecolor": INK["primary"], "axes.titleweight": "bold",
        "xtick.color": INK["muted"], "ytick.color": INK["muted"],
        "xtick.labelcolor": INK["secondary"], "ytick.labelcolor": INK["secondary"],
        "axes.grid": True, "grid.color": INK["grid"], "grid.linewidth": 0.6,
        "lines.linewidth": 1.6, "font.size": 9, "axes.titlesize": 10,
        "legend.frameon": False, "text.color": INK["primary"],
        "font.family": "sans-serif",
    })
    return plt
