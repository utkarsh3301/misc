"""
Daily EMA crossover experiments.

A. NIFTY and BANKNIFTY indices (2007/2010 to Oct 2026)
   classic pairs, a full fast/slow grid, filter variants, in-sample /
   out-of-sample selection, random entry significance tests
B. 62 NSE stocks (2005 to Oct 2026), long only, delivery costs
C. Global markets (OANDA CFDs 2005-2020, BTC 2012-2017), daily and hourly

Writes CSV tables to results/tables, figures to results/figures and a
markdown digest to results/ema_daily.md.

Usage: python scripts/run_ema_daily.py
"""

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from ema_lab import costs, data, engine, metrics, stats
from ema_lab import strategies as st
from ema_lab.report_utils import (INK, SERIES, diverging_cmap, fig_path, label_line_ends, markdown,
                                  save_table, setup_matplotlib)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_data import EOD_FORMER, EOD_STOCKS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS = [(5, 20), (9, 21), (12, 26), (20, 50), (50, 100), (50, 200)]
FAST_GRID = [3, 5, 8, 10, 13, 15, 20, 25, 30, 40, 50]
SLOW_GRID = [20, 30, 40, 50, 60, 80, 100, 120, 150, 200]
IDX_COST = costs.per_side(costs.NSE_FUTURES_2026)
STOCK_COST = costs.per_side(costs.NSE_DELIVERY)
N_SIMS = 1000
# Every daily statistic starts this many bars into each series, so all
# rules (the slowest needs 200 bars of EMA history) and buy and hold are
# measured over the same window.
WARMUP = 200

COLS = ["trades", "win_rate", "profit_factor", "expectancy_bps", "cagr", "sharpe", "max_dd",
        "exposure", "trades_per_year", "bh_cagr", "bh_sharpe", "bh_max_dd"]


def start_of(df):
    return df.index[min(WARMUP, len(df) - 1)]


def evaluate(df, sig, cost, label=None, random_test=False, same_day=False):
    r = engine.run(df, sig, cost)
    start = start_of(df)
    s = metrics.summarize(r, df, start=start)
    s["expectancy_bps"] = s["expectancy"] * 1e4
    if random_test:
        trades = r.trades[r.trades.entry_time >= start]
        rt = stats.random_entry_test(df, trades, cost, n_sims=N_SIMS, same_day=same_day)
        s["p_random"] = rt["p_value"]
        s["random_mean_bps"] = rt["random_mean"] * 1e4
    if label:
        s.update(label)
    return s, r


def window_stats(r, start=None, end=None):
    """Stats for a sub-period of a full-history run (EMAs warmed up on the earlier data)."""
    ret = r.returns.loc[start:end]
    tr = r.trades[(r.trades.entry_time >= (start or r.returns.index[0]))
                  & (r.trades.entry_time <= (end or r.returns.index[-1]))]
    s = metrics.trade_stats(tr)
    s.update(metrics.equity_stats(ret))
    return s


# ---------------------------------------------------------------------------
# A. Indices
# ---------------------------------------------------------------------------

def run_indices(md):
    plt = setup_matplotlib()
    indices = {s: data.load_index_daily(s) for s in ["NIFTY", "BANKNIFTY"]}

    # A1 classic pairs
    rows = []
    for sym, df in indices.items():
        for fast, slow in PAIRS:
            for side in ["long_only", "long_short"]:
                s, _ = evaluate(df, st.ema_cross(df, fast, slow, side), IDX_COST,
                                {"market": sym, "rule": f"EMA {fast}/{slow}", "side": side},
                                random_test=True)
                rows.append(s)
    t = pd.DataFrame(rows)
    save_table(t, "A1_index_classic_pairs")
    md.append("## A1. Classic EMA pairs on NIFTY and BANKNIFTY (daily, 2026 futures costs)\n")
    for sym, df in indices.items():
        md.append(f"**{sym}**, statistics from {start_of(df):%d %b %Y} (after a {WARMUP} bar EMA warm-up "
                  f"on data from {df.index[0]:%b %Y}) to {df.index[-1]:%d %b %Y}\n")
        md.append(markdown(t[t.market == sym], ["rule", "side"] + COLS[:9] + ["p_random"]))
        bh = t[t.market == sym].iloc[0]
        md.append(f"\nBuy and hold: CAGR {bh.bh_cagr:.1%}, Sharpe {bh.bh_sharpe:.2f}, "
                  f"max drawdown {bh.bh_max_dd:.1%}.\n")

    # A2 grid
    grid_rows = []
    for sym, df in indices.items():
        for side in ["long_only", "long_short"]:
            for fast in FAST_GRID:
                for slow in SLOW_GRID:
                    if fast >= slow:
                        continue
                    r = engine.run(df, st.ema_cross(df, fast, slow, side), IDX_COST)
                    s = metrics.summarize(r, df, start=start_of(df))
                    s.update({"market": sym, "side": side, "fast": fast, "slow": slow})
                    grid_rows.append(s)
    g = pd.DataFrame(grid_rows)
    save_table(g, "A2_index_grid")
    gs_pairs = [(f, s_) for f in FAST_GRID for s_ in SLOW_GRID if f < s_]

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for i, sym in enumerate(indices):
        for j, side in enumerate(["long_only", "long_short"]):
            sub = g[(g.market == sym) & (g.side == side)]
            piv = sub.pivot(index="fast", columns="slow", values="sharpe")
            bh = sub.bh_sharpe.iloc[0]
            ax = axes[i, j]
            lim = max(abs(piv.min().min() - bh), abs(piv.max().max() - bh))
            im = ax.imshow(piv.values, cmap=diverging_cmap(), vmin=bh - lim, vmax=bh + lim, aspect="auto")
            ax.set_xticks(range(len(piv.columns)), piv.columns)
            ax.set_yticks(range(len(piv.index)), piv.index)
            ax.set_xlabel("slow EMA")
            ax.set_ylabel("fast EMA")
            ax.grid(False)
            for (a, b), v in np.ndenumerate(piv.values):
                if np.isfinite(v):
                    ax.text(b, a, f"{v:.2f}", ha="center", va="center", fontsize=6.5,
                            color=INK["primary"])
            ax.set_title(f"{sym} {side.replace('_', ' ')}: Sharpe (buy and hold {bh:.2f} = gray)")
            fig.colorbar(im, ax=ax, shrink=0.8)
    fig.suptitle("Daily EMA crossover Sharpe ratio across the parameter grid, after 2026 costs",
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(fig_path("A2_index_grid_sharpe"))
    plt.close(fig)

    md.append(f"## A2. Parameter grid ({len(gs_pairs)} fast/slow pairs per market and side)\n")
    grid_summary = []
    for (sym, side), sub in g.groupby(["market", "side"]):
        n = len(sub)
        e_max = stats.expected_max_sharpe(n, sub.sharpe.std())
        grid_summary.append({
            "market": sym, "side": side, "pairs": n,
            "share_beating_bh_sharpe_pct": (sub.sharpe > sub.bh_sharpe).mean(),
            "share_beating_bh_cagr_pct": (sub.cagr > sub.bh_cagr).mean(),
            "share_pf_above_1_pct": (sub.profit_factor > 1).mean(),
            "median_sharpe": sub.sharpe.median(), "best_sharpe": sub.sharpe.max(),
            "best_pair": "{}/{}".format(*sub.loc[sub.sharpe.idxmax(), ["fast", "slow"]].astype(int)),
            "median_win_rate": sub.win_rate.median(),
            "bh_sharpe": sub.bh_sharpe.iloc[0],
            "luck_threshold_sharpe": sub.sharpe.median() + e_max,
        })
    gs = pd.DataFrame(grid_summary)
    save_table(gs, "A2_index_grid_summary")
    md.append(markdown(gs, rename={"share_beating_bh_sharpe_pct": "beats B&H Sharpe",
                                   "share_beating_bh_cagr_pct": "beats B&H CAGR",
                                   "share_pf_above_1_pct": "PF > 1"}))
    md.append("\n`luck_threshold_sharpe` is the grid median plus the expected maximum of "
              f"{len(gs_pairs)} zero-skill trials (Bailey and Lopez de Prado); a best "
              "pair below it is consistent with data mining luck.\n")
    md.append("![grid](figures/A2_index_grid_sharpe.png)\n")

    # A3 variants
    variants = [
        ("EMA 20/50", lambda d: st.ema_cross(d, 20, 50, "long_only")),
        ("EMA 20/50 + close > EMA 200", lambda d: st.ema_cross_filtered(d, 20, 50, "long_only", trend_ema=200)),
        ("EMA 20/50 + ADX > 20", lambda d: st.ema_cross_filtered(d, 20, 50, "long_only", adx_min=20)),
        ("EMA 20/50 + 2 ATR stop", lambda d: st.ema_cross_filtered(d, 20, 50, "long_only", atr_stop=2.0)),
        ("EMA 20/50 + 3 ATR trailing stop", lambda d: st.ema_cross_filtered(d, 20, 50, "long_only", atr_trail=3.0)),
        ("EMA 9/21 + close > EMA 200", lambda d: st.ema_cross_filtered(d, 9, 21, "long_only", trend_ema=200)),
        ("Triple EMA 10/20/50", lambda d: st.triple_ema(d, 10, 20, 50, "long_only")),
        ("MACD 12/26/9", lambda d: st.macd_cross(d, 12, 26, 9, "long_only")),
        ("Close > EMA 50", lambda d: st.price_vs_ema(d, 50, "long_only")),
        ("Close > EMA 100", lambda d: st.price_vs_ema(d, 100, "long_only")),
        ("Close > EMA 200", lambda d: st.price_vs_ema(d, 200, "long_only")),
        ("EMA 20/50 long/short", lambda d: st.ema_cross(d, 20, 50, "long_short")),
        ("EMA 20/50 long/short + EMA 200 regime", lambda d: st.ema_cross_filtered(d, 20, 50, "long_short", trend_ema=200)),
        ("EMA 20/50 long/short + ADX > 25", lambda d: st.ema_cross_filtered(d, 20, 50, "long_short", adx_min=25)),
        ("MACD 12/26/9 long/short", lambda d: st.macd_cross(d, 12, 26, 9, "long_short")),
    ]
    rows = []
    runs = {}
    for sym, df in indices.items():
        for name, fn in variants:
            s, r = evaluate(df, fn(df), IDX_COST, {"market": sym, "rule": name}, random_test=True)
            rows.append(s)
            runs[(sym, name)] = r
    v = pd.DataFrame(rows)
    save_table(v, "A3_index_variants")
    md.append("## A3. Filters and EMA family variants (daily, 2026 futures costs)\n")
    for sym in indices:
        md.append(f"**{sym}**\n")
        md.append(markdown(v[v.market == sym], ["rule"] + COLS[:9] + ["p_random"]))
        md.append("")

    # A3b total return view: cash interest when flat, dividends when long
    rows = []
    for sym, df in indices.items():
        start = start_of(df)
        bh_ret = (df["close"].pct_change().fillna(0) + 0.013 / 252).loc[start:]
        bh = metrics.equity_stats(bh_ret)
        for name in ["EMA 20/50", "EMA 20/50 + 3 ATR trailing stop", "Triple EMA 10/20/50",
                     "Close > EMA 50", "EMA 20/50 long/short"]:
            r = runs[(sym, name)]
            e = metrics.equity_stats(metrics.with_carry(r).loc[start:])
            rows.append({"market": sym, "rule": name, "cagr": e["cagr"], "sharpe": e["sharpe"],
                         "max_dd": e["max_dd"], "bh_cagr": bh["cagr"], "bh_sharpe": bh["sharpe"],
                         "bh_max_dd": bh["max_dd"]})
    tv = pd.DataFrame(rows)
    save_table(tv, "A3b_index_total_return")
    md.append("## A3b. Total return view (6% a year on idle cash, 1.3% dividend yield while long)\n")
    md.append("Price-only backtests penalise rules that spend a third of the time in cash. With a "
              "constant 6% cash yield (overnight TREPS averaged about 5.4% over 2016-2026 per the "
              "NIFTY 1D Rate Index, T-bills were higher before) and 1.3% dividends for whoever holds "
              "the index:\n")
    md.append(markdown(tv))
    md.append("")

    # A4 in-sample / out-of-sample
    md.append("## A4. Pick the best pair in-sample, test it out-of-sample\n")
    split = {"NIFTY": "2016-12-31", "BANKNIFTY": "2017-12-31"}
    rows = []
    for sym, df in indices.items():
        cut = pd.Timestamp(split[sym])
        for side in ["long_only", "long_short"]:
            res = []
            for fast in FAST_GRID:
                for slow in SLOW_GRID:
                    if fast >= slow:
                        continue
                    r = engine.run(df, st.ema_cross(df, fast, slow, side), IDX_COST)
                    ins = window_stats(r, start=start_of(df), end=cut)
                    oos = window_stats(r, start=cut + pd.Timedelta(days=1))
                    res.append((fast, slow, ins["sharpe"], oos["sharpe"], oos["cagr"], oos["max_dd"],
                                oos["win_rate"], oos["trades"]))
            res = pd.DataFrame(res, columns=["fast", "slow", "is_sharpe", "oos_sharpe", "oos_cagr",
                                             "oos_max_dd", "oos_win_rate", "oos_trades"])
            best = res.loc[res.is_sharpe.idxmax()]
            rank = int((res.oos_sharpe > best.oos_sharpe).sum()) + 1
            bh_oos = metrics.equity_stats(df["close"].pct_change().fillna(0).loc[cut + pd.Timedelta(days=1):])
            corr = res[["is_sharpe", "oos_sharpe"]].corr(method="spearman").iloc[0, 1]
            rows.append({"market": sym, "side": side, "in_sample": f"to {cut:%Y}",
                         "best_is_pair": f"{int(best.fast)}/{int(best.slow)}",
                         "is_sharpe": best.is_sharpe, "oos_sharpe": best.oos_sharpe,
                         "oos_rank": f"{rank} of {len(res)}", "oos_cagr": best.oos_cagr, "oos_max_dd": best.oos_max_dd,
                         "oos_win_rate": best.oos_win_rate, "oos_bh_sharpe": bh_oos["sharpe"],
                         "oos_bh_cagr": bh_oos["cagr"], "is_oos_rank_corr": corr})
    oo = pd.DataFrame(rows)
    save_table(oo, "A4_index_is_oos")
    md.append(markdown(oo, rename={"oos_win_rate": "oos win rate"}))
    md.append("\n`is_oos_rank_corr` is the Spearman correlation between in-sample and out-of-sample "
              "Sharpe across all grid pairs: near zero means past parameter rankings told you nothing "
              "about future ones.\n")

    # Equity curve figure for NIFTY
    df = indices["NIFTY"]
    start = start_of(df)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1.3]})
    bh = (1 + df["close"].pct_change().fillna(0).loc[start:]).cumprod()
    curves = [("Buy and hold", bh, INK["secondary"])]
    for k, (name, color) in enumerate([("EMA 20/50", SERIES[0]), ("Close > EMA 50", SERIES[1]),
                                       ("EMA 20/50 long/short", SERIES[2])]):
        curves.append((name, (1 + runs[("NIFTY", name)].returns.loc[start:]).cumprod(), color))
    for name, eq, color in curves:
        ax1.plot(eq.index, eq.values, color=color, lw=1.6 if name != "Buy and hold" else 1.2, label=name)
        dd = eq / eq.cummax() - 1
        ax2.plot(dd.index, dd.values * 100, color=color, lw=1.0)
    ax1.set_yscale("log")
    label_line_ends(ax1, [(n, e.index[-1], e.values[-1]) for n, e, _ in curves])
    ax1.set_ylabel("growth of 1 (log scale)")
    ax1.legend(loc="upper left")
    ax1.set_title("NIFTY 50 daily: EMA rules vs buy and hold, after 2026 futures costs")
    ax2.set_ylabel("drawdown %")
    fig.tight_layout()
    fig.savefig(fig_path("A_nifty_equity"))
    plt.close(fig)
    md.append("![nifty equity](figures/A_nifty_equity.png)\n")

    # yearly table for the main rule
    yr = pd.DataFrame({
        "NIFTY buy and hold": metrics.yearly_returns(df["close"].pct_change().fillna(0).loc[start:]),
        "EMA 20/50 long only": metrics.yearly_returns(runs[("NIFTY", "EMA 20/50")].returns.loc[start:]),
        "EMA 20/50 long/short": metrics.yearly_returns(runs[("NIFTY", "EMA 20/50 long/short")].returns.loc[start:]),
    })
    yr.index.name = "year"
    yr = yr.reset_index()
    save_table(yr, "A5_nifty_yearly")
    md.append(f"## A5. NIFTY calendar year returns (from {start:%d %b %Y}, after the 200 bar warm-up)\n")
    md.append(markdown(yr.rename(columns=lambda c: c if c == "year" else c + "_pct")))
    md.append("")
    return indices


# ---------------------------------------------------------------------------
# B. NSE stocks
# ---------------------------------------------------------------------------

def run_stocks(md):
    plt = setup_matplotlib()
    universe = [(s, "survivor") for s in EOD_STOCKS] + [(s, "former member") for s in EOD_FORMER]
    frames = {s: data.load_eod(s) for s, _ in universe}
    groups = dict(universe)
    rows = []
    port = {}
    for fast, slow in [(9, 21), (20, 50), (50, 200)]:
        strat_rets, bh_rets = {}, {}
        for name, df in frames.items():
            if len(df) < 500:
                continue
            r = engine.run(df, st.ema_cross(df, fast, slow, "long_only"), STOCK_COST)
            start = start_of(df)
            s = metrics.summarize(r, df, start=start)
            s.update({"stock": name, "group": groups[name], "rule": f"EMA {fast}/{slow}",
                      "expectancy_bps": s["expectancy"] * 1e4})
            rows.append(s)
            # both legs join the portfolio at the same date
            strat_rets[name] = r.returns.loc[start:]
            bh_rets[name] = df["close"].pct_change().fillna(0).loc[start:]
        sr = pd.DataFrame(strat_rets).sort_index()
        br = pd.DataFrame(bh_rets).sort_index()
        # Equal weight across the stocks listed on each day; a stock enters
        # the portfolio from its first bar.
        port[f"EMA {fast}/{slow}"] = sr.mean(axis=1, skipna=True)
        port["Buy and hold"] = br.mean(axis=1, skipna=True)
    t = pd.DataFrame(rows)
    save_table(t, "B1_stock_results")

    agg = []
    for (rule, group), sub in list(t.groupby(["rule", "group"])) + [((r, "all"), s) for r, s in t.groupby("rule")]:
        agg.append({
            "rule": rule, "group": group, "stocks": len(sub),
            "median_cagr": sub.cagr.median(), "median_bh_cagr": sub.bh_cagr.median(),
            "beats_bh_cagr_pct": (sub.cagr > sub.bh_cagr).mean(),
            "beats_bh_sharpe_pct": (sub.sharpe > sub.bh_sharpe).mean(),
            "pf_above_1_pct": (sub.profit_factor > 1).mean(),
            "mean_win_rate": sub.win_rate.mean(),
            "median_max_dd": sub.max_dd.median(), "median_bh_max_dd": sub.bh_max_dd.median(),
            "median_trades_per_year": sub.trades_per_year.median(),
        })
    a = pd.DataFrame(agg).sort_values(["rule", "group"])
    save_table(a, "B1_stock_summary")
    md.append("## B1. EMA crossovers on 62 NSE stocks (daily, long only, delivery costs ~29 bps round trip)\n")
    md.append("Survivors are current or recent Nifty 50 members; former members are stocks that "
              "dropped out of the index (Yes Bank, Vodafone Idea, RCom, Unitech, JP Associates, "
              "Suzlon, DLF, Zee, Vedanta, ...), included to blunt survivorship bias. Data from 2005 "
              "or listing date to Oct 2026.\n")
    md.append(markdown(a, rename={"beats_bh_cagr_pct": "beats B&H CAGR", "beats_bh_sharpe_pct": "beats B&H Sharpe",
                                  "pf_above_1_pct": "PF > 1"}))
    md.append("")

    prow = []
    for name, ret in port.items():
        s = metrics.equity_stats(ret.fillna(0))
        s["portfolio"] = name
        prow.append(s)
    p = pd.DataFrame(prow)[["portfolio", "cagr", "vol", "sharpe", "max_dd", "calmar"]]
    save_table(p, "B2_stock_portfolios")
    md.append("## B2. Equal weight portfolios across the same 62 stocks\n")
    md.append(markdown(p))
    md.append("")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    names = list(port)
    order = ["Buy and hold"] + [n for n in names if n != "Buy and hold"]
    ends = []
    for k, name in enumerate(order):
        eq = (1 + port[name].fillna(0)).cumprod()
        color = INK["secondary"] if name == "Buy and hold" else SERIES[k - 1]
        ax.plot(eq.index, eq.values, color=color, lw=1.2 if name == "Buy and hold" else 1.6, label=name)
        ends.append((name, eq.index[-1], eq.values[-1]))
    ax.set_yscale("log")
    label_line_ends(ax, ends)
    ax.set_ylabel("growth of 1 (log scale)")
    ax.legend(loc="upper left")
    ax.set_title("Equal weight, 62 NSE stocks: EMA crossover (long only, after delivery costs) vs buy and hold")
    fig.tight_layout()
    fig.savefig(fig_path("B_stock_portfolio"))
    plt.close(fig)
    md.append("![stocks](figures/B_stock_portfolio.png)\n")

    fig, ax = plt.subplots(figsize=(10, 4))
    sub = t[t.rule == "EMA 20/50"].copy()
    sub["gap"] = (sub.cagr - sub.bh_cagr) * 100
    sub = sub.sort_values("gap")
    colors = [SERIES[0] if g == "survivor" else SERIES[1] for g in sub.group]
    ax.bar(range(len(sub)), sub.gap, color=colors, width=0.8)
    ax.axhline(0, color=INK["axis"], lw=1)
    ax.set_xticks(range(len(sub)), sub.stock, rotation=90, fontsize=6)
    ax.set_ylabel("strategy CAGR minus buy and hold CAGR, pts")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=SERIES[0], label="survivor"), Patch(color=SERIES[1], label="former member")],
              loc="upper left")
    ax.set_title("EMA 20/50 long only vs buy and hold, per stock (after delivery costs)")
    fig.tight_layout()
    fig.savefig(fig_path("B_stock_cagr_gap"))
    plt.close(fig)
    md.append("![per stock](figures/B_stock_cagr_gap.png)\n")


# ---------------------------------------------------------------------------
# C. Global markets
# ---------------------------------------------------------------------------

def run_global(md):
    rows = []
    for inst in data.MULTI_ASSETS:
        cost = costs.per_side(costs.GLOBAL[inst])
        for freq in ["1d", "1h"]:
            df = data.load_multi(inst, freq)
            pairs = [(9, 21), (20, 50), (50, 200)]
            for fast, slow in pairs:
                for side in ["long_only", "long_short"]:
                    s, _ = evaluate(df, st.ema_cross(df, fast, slow, side), cost,
                                    {"market": inst, "bars": freq, "rule": f"EMA {fast}/{slow}", "side": side},
                                    random_test=(freq == "1d"))
                    rows.append(s)
    t = pd.DataFrame(rows)
    save_table(t, "C1_global")
    md.append("## C1. Global markets (OANDA CFDs Jan 2005 to May 2020, Bitstamp BTC 2012-2017)\n")
    md.append("Daily bars, after spread and slippage costs. `p_random` is the random entry test.\n")
    md.append(markdown(t[t.bars == "1d"], ["market", "rule", "side"] + COLS[:9] + ["bh_cagr", "p_random"]))
    md.append("\nHourly bars, same rules (the EMA lengths now span hours, not days):\n")
    md.append(markdown(t[t.bars == "1h"], ["market", "rule", "side", "trades", "win_rate", "profit_factor",
                                            "expectancy_bps", "cagr", "sharpe", "max_dd", "trades_per_year"]))
    md.append("")


def main():
    t0 = time.time()
    md = ["# Daily EMA crossover results\n",
          "Generated by `scripts/run_ema_daily.py`. All fills at the next bar's open, costs per side as in "
          "`ema_lab/costs.py`. Win rate = share of trades with a positive return after costs. "
          f"`p_random` = share of {N_SIMS} random-entry strategies (same trade count, holding periods "
          "and direction) with a mean trade at least as good; below 0.05 suggests the timing is "
          "doing something.\n"]
    run_indices(md)
    print(f"[A] indices done {time.time() - t0:.0f}s")
    run_stocks(md)
    print(f"[B] stocks done {time.time() - t0:.0f}s")
    run_global(md)
    print(f"[C] global done {time.time() - t0:.0f}s")
    with open(os.path.join(ROOT, "results", "ema_daily.md"), "w") as f:
        f.write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()
