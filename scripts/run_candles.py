"""
Candlestick price action experiments.

E. Event study: after each pattern, how often does price move the way
   the pattern predicts over the next h bars (the "success percentage"),
   and is that better than (a) any bar and (b) any bar with the same
   prior trend? Entry is the next bar's open, exit the close h bars later.
F. Tradable versions: next open entry, stop beyond the pattern bar's
   extreme, 2R target, time stop, real costs.
G. Hybrid: EMA trend filter + pullback to the 20 EMA + candle trigger,
   against control entries that drop the candle requirement.

Universes: 62 NSE stocks daily (2005-2026), NIFTY and BANKNIFTY daily,
7 global markets daily (2005-2020), NIFTY and BANKNIFTY 15-minute bars
(2011-Feb 2023).

Usage: python scripts/run_candles.py
"""

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from ema_lab import costs, data, engine, metrics, patterns, stats
from ema_lab import strategies as st
from ema_lab.report_utils import INK, SERIES, fig_path, markdown, save_table, setup_matplotlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_data import EOD_FORMER, EOD_STOCKS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N_SIMS = 500
DAILY_H = [1, 5, 10]
INTRA_H = [1, 4, 8]
TRIGGERS_BULL = ["bullish_engulfing", "hammer", "bullish_pin_bar", "morning_star", "piercing_line"]
TRIGGERS_BEAR = ["bearish_engulfing", "shooting_star", "bearish_pin_bar", "evening_star", "dark_cloud_cover"]


# ---------------------------------------------------------------------------
# universes
# ---------------------------------------------------------------------------

def universes():
    u = {}
    stocks = {}
    for s in EOD_STOCKS + EOD_FORMER:
        df = data.load_eod(s)
        if len(df) > 500:
            stocks[s] = df
    u["NSE stocks (daily)"] = {"frames": stocks, "kind": "daily",
                               "cost_long": costs.NSE_DELIVERY, "cost_short": costs.NSE_STOCK_FUTURES}
    u["NSE indices (daily)"] = {"frames": {s: data.load_index_daily(s) for s in ["NIFTY", "BANKNIFTY"]},
                                "kind": "daily", "cost_long": costs.NSE_FUTURES_2026,
                                "cost_short": costs.NSE_FUTURES_2026}
    u["Global markets (daily)"] = {"frames": {m: data.load_multi(m, "1d") for m in data.MULTI_ASSETS},
                                   "kind": "daily", "cost_long": None, "cost_short": None}
    u["NIFTY/BANKNIFTY (15m)"] = {"frames": {s: data.resample_session(data.load_intraday(s), 15)
                                             for s in ["NIFTY", "BANKNIFTY"]},
                                  "kind": "intraday", "cost_long": costs.NSE_FUTURES_2026,
                                  "cost_short": costs.NSE_FUTURES_2026}
    return u


def cost_for(u, name, direction):
    bps = u["cost_long"] if direction == 1 else u["cost_short"]
    if bps is None:
        bps = costs.GLOBAL[name]
    return costs.per_side(bps)


# ---------------------------------------------------------------------------
# E. event study
# ---------------------------------------------------------------------------

def forward_returns(df, horizons, intraday):
    o = df["open"].to_numpy()
    c = df["close"].to_numpy()
    n = len(df)
    out = {}
    day = df.index.normalize().to_numpy() if intraday else None
    for h in horizons:
        f = np.full(n, np.nan)
        if n > h:
            f[:n - h] = c[h:] / o[1:n - h + 1] - 1.0
            if intraday:
                same = np.zeros(n, bool)
                same[:n - h] = day[h:] == day[:n - h]
                f[~same] = np.nan
        out[h] = f
    return out


def cluster_t(x, groups):
    """t-stat of mean(x) > 0 with standard errors clustered by group (CR0)."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return np.nan
    e = x - x.mean()
    s = pd.Series(e).groupby(np.asarray(groups)).sum().to_numpy()
    g = len(s)
    if g < 5:
        return np.nan
    var = (s ** 2).sum() / n ** 2 * g / (g - 1)
    return x.mean() / np.sqrt(var) if var > 0 else np.nan


def event_study(u_name, u):
    intraday = u["kind"] == "intraday"
    horizons = INTRA_H if intraday else DAILY_H
    events = []
    base = []
    for name, df in u["frames"].items():
        pat = patterns.detect(df)
        ctx = patterns.trend_context(df).to_numpy()
        fwd = forward_returns(df, horizons, intraday)
        # Week buckets for daily data (absorbs same-day cross-sectional
        # correlation and most overlap at h <= 5), sessions for intraday.
        if intraday:
            cluster = df.index.normalize().to_numpy()
        else:
            cluster = (df.index - pd.Timestamp("2000-01-03")).days.to_numpy() // 7
        warm = np.arange(len(df)) >= 30
        b = pd.DataFrame({"instrument": name, "date": df.index, "ctx": ctx, "cluster": cluster,
                          **{f"f{h}": fwd[h] for h in horizons}})[warm]
        base.append(b)
        for p, (direction, _kind) in patterns.PATTERNS.items():
            m = pat[p].to_numpy() & warm
            if not m.any():
                continue
            in_ctx = patterns.in_context(p, pd.Series(ctx)).to_numpy()
            ev = pd.DataFrame({"instrument": name, "pattern": p, "direction": direction,
                               "date": df.index[m], "in_context": in_ctx[m], "ctx": ctx[m], "cluster": cluster[m],
                               **{f"f{h}": fwd[h][m] for h in horizons}})
            events.append(ev)
    ev = pd.concat(events, ignore_index=True)
    base = pd.concat(base, ignore_index=True)

    return summarize_events(ev, base, u_name, horizons), horizons, ev, base


def summarize_events(ev, base, u_name, horizons):
    rows = []
    for p, (direction, kind) in patterns.PATTERNS.items():
        sub_all = ev[ev.pattern == p]
        for scope in ["all", "in context"]:
            sub = sub_all if scope == "all" else sub_all[sub_all.in_context]
            if scope == "all":
                ref = base
            else:
                want = -direction if kind == "reversal" else direction
                ref = base[base.ctx == want]
            row = {"universe": u_name, "pattern": p, "direction": "bullish" if direction == 1 else "bearish",
                   "type": kind, "scope": scope, "events": len(sub)}
            for h in horizons:
                x = direction * sub[f"f{h}"].dropna()
                bref = direction * ref[f"f{h}"].dropna()
                hit = (x > 0).mean() if len(x) else np.nan
                base_hit = (bref > 0).mean()
                row[f"hit_rate_{h}"] = hit
                row[f"base_hit_rate_{h}"] = base_hit
                row[f"mean_bps_{h}"] = x.mean() * 1e4 if len(x) else np.nan
                row[f"base_mean_bps_{h}"] = bref.mean() * 1e4
                excess = x - bref.mean()
                row[f"t_{h}"] = cluster_t(excess.to_numpy(), sub.loc[x.index, "cluster"].to_numpy())
                row[f"p_binom_{h}"] = stats.binomial_p((x > 0).sum(), len(x), base_hit) if len(x) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def split_half(e, ev, base, u_name, horizons):
    """Re-test each |t| > 2 finding separately in each half of the sample."""
    h = horizons[1]
    hits = e[e[f"t_{h}"].abs() > 2]
    if hits.empty:
        return pd.DataFrame()
    cut = base["date"].quantile(0.5)
    rows = []
    for half, sel_ev, sel_base in [("first half", ev.date <= cut, base.date <= cut),
                                   ("second half", ev.date > cut, base.date > cut)]:
        res = summarize_events(ev[sel_ev], base[sel_base], u_name, horizons)
        for _, r in hits.iterrows():
            m = res[(res.pattern == r.pattern) & (res.scope == r.scope)].iloc[0]
            rows.append({"universe": u_name, "pattern": r.pattern, "scope": r.scope, "half": half,
                         "split_date": f"{cut:%Y-%m-%d}", "full_sample_t": r[f"t_{h}"],
                         "events": m.events, "hit_rate": m[f"hit_rate_{h}"],
                         "base_hit_rate": m[f"base_hit_rate_{h}"], "t": m[f"t_{h}"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# F. tradable pattern strategies
# ---------------------------------------------------------------------------

def pooled(items, intraday):
    """Pool trades over instruments: stats, bootstrap CI, random entry baseline."""
    trades = [t for _, t, _ in items if len(t)]
    if not trades:
        empty = metrics.trade_stats(pd.DataFrame({"ret": [], "bars": []}))
        return empty, (np.nan, np.nan), {"p_value": np.nan, "random_mean": np.nan}
    t = pd.concat(trades, ignore_index=True)
    s = metrics.trade_stats(t)
    ci = stats.bootstrap_mean_ci(t["ret"].to_numpy(), n_boot=2000)
    rt = stats.random_entry_pooled(items, n_sims=N_SIMS, same_day=intraday)
    return s, ci, rt


def detect_all(u):
    return {name: (patterns.detect(df), patterns.trend_context(df)) for name, df in u["frames"].items()}


def tradable(u_name, u, cache):
    intraday = u["kind"] == "intraday"
    hold = 8 if intraday else 10
    rows = []
    for p, (direction, kind) in patterns.PATTERNS.items():
        items = []
        for name, df in u["frames"].items():
            pat, ctx = cache[name]
            mask = pat[p].to_numpy() & patterns.in_context(p, ctx).to_numpy()
            mask[:30] = False
            if not mask.any():
                continue
            sig = st.pattern_trades(df, mask, direction, hold=hold, rr=2.0)
            if intraday:
                sig = st.with_session(sig, df.index)
            cost = cost_for(u, name, direction)
            r = engine.run(df, sig, cost)
            items.append((df, r.trades.assign(instrument=name), cost))
        s, ci, rt = pooled(items, intraday)
        rows.append({"universe": u_name, "pattern": p, "direction": "bullish" if direction == 1 else "bearish",
                     "trades": s["trades"], "win_rate": s["win_rate"], "payoff": s["payoff"],
                     "profit_factor": s["profit_factor"], "expectancy_bps": s["expectancy"] * 1e4,
                     "ci_low_bps": ci[0] * 1e4, "ci_high_bps": ci[1] * 1e4,
                     "random_mean_bps": rt["random_mean"] * 1e4, "p_random": rt["p_value"],
                     "avg_bars": s["avg_bars"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# G. EMA pullback + candle trigger
# ---------------------------------------------------------------------------

def hybrid(u_name, u, cache):
    intraday = u["kind"] == "intraday"
    hold = 16 if intraday else 20
    rows = []
    for direction, triggers in [(1, TRIGGERS_BULL), (-1, TRIGGERS_BEAR)]:
        setups = {
            "any candle trigger": None,
            "control: any bar closing in trend direction": "close",
            "control: any bar touching the EMA": "touch",
        }
        for label, control in setups.items():
            items = []
            for name, df in u["frames"].items():
                pat = cache[name][0]
                if control is None:
                    m = pat[triggers].any(axis=1).to_numpy()
                elif control == "close":
                    m = (direction * (df["close"] - df["open"]) > 0).to_numpy()
                else:
                    m = np.ones(len(df), bool)
                # Controls stop beyond the signal bar's extreme too, so the
                # risk unit matches the candle version.
                sig, mask = st.ema_pullback_pattern(df, m, direction, hold=hold, rr=2.0)
                if intraday:
                    sig = st.with_session(sig, df.index)
                cost = cost_for(u, name, direction)
                r = engine.run(df, sig, cost)
                items.append((df, r.trades.assign(instrument=name), cost))
            s, ci, rt = pooled(items, intraday)
            rows.append({"universe": u_name, "side": "long" if direction == 1 else "short", "entry": label,
                         "trades": s["trades"], "win_rate": s["win_rate"], "payoff": s["payoff"],
                         "profit_factor": s["profit_factor"], "expectancy_bps": s["expectancy"] * 1e4,
                         "ci_low_bps": ci[0] * 1e4, "ci_high_bps": ci[1] * 1e4,
                         "random_mean_bps": rt["random_mean"] * 1e4, "p_random": rt["p_value"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    plt = setup_matplotlib()
    us = universes()
    print(f"loaded {time.time() - t0:.0f}s")
    md = ["# Candlestick price action results\n",
          "Generated by `scripts/run_candles.py`. Pattern rules are in `ema_lab/patterns.py`. "
          "A pattern is detected at a bar's close and traded from the next bar's open.\n",
          "**Success percentage (hit rate)** = share of pattern occurrences where price moved in the "
          "predicted direction between the next open and the close h bars later. Each is compared "
          "with the base rate for any bar (`all` rows) or for any bar with the same prior trend "
          "(`in context` rows: reversal patterns after a move against them, continuation patterns "
          "after a move with them). `t` is the t-statistic of the excess mean return over that base "
          "rate with standard errors clustered by week (daily) or session (15m). |t| > 2 is the usual "
          "bar, but with 22 patterns x 2 scopes x 3 horizons x 4 universes, expect a handful of "
          "|t| > 2 results from luck alone.\n"]

    all_e, all_f, all_g, all_split = [], [], [], []
    for u_name, u in us.items():
        e, horizons, ev, base = event_study(u_name, u)
        all_e.append(e)
        all_split.append(split_half(e, ev, base, u_name, horizons))
        print(f"E {u_name} {time.time() - t0:.0f}s")
        cache = detect_all(u)
        f = tradable(u_name, u, cache)
        all_f.append(f)
        print(f"F {u_name} {time.time() - t0:.0f}s")
        g = hybrid(u_name, u, cache)
        all_g.append(g)
        print(f"G {u_name} {time.time() - t0:.0f}s")

        h_mid = horizons[1]
        md.append(f"## E. {u_name}: success percentage after each pattern\n")
        cols = ["pattern", "scope", "events"]
        for h in horizons:
            cols += [f"hit_rate_{h}", f"base_hit_rate_{h}"]
        cols += [f"mean_bps_{h_mid}", f"base_mean_bps_{h_mid}", f"t_{h_mid}"]
        unit = "15m bars" if u["kind"] == "intraday" else "days"
        md.append(f"Horizons {horizons} {unit}. Mean and t columns are for h = {h_mid}.\n")
        md.append(markdown(e, cols))
        md.append("")

    E = pd.concat(all_e, ignore_index=True)
    F = pd.concat(all_f, ignore_index=True)
    G = pd.concat(all_g, ignore_index=True)
    save_table(E, "E_candles_event_study")
    save_table(F, "F_candles_tradable")
    save_table(G, "G_ema_pullback_candles")
    S = pd.concat(all_split, ignore_index=True)
    save_table(S, "E2_split_half")
    n_tests = int(E[[c for c in E.columns if c.startswith("t_")]].notna().sum().sum())
    n_sig = int((E[[c for c in E.columns if c.startswith("t_")]].abs() > 2).sum().sum())
    md.append("## E2. Do the significant findings replicate in each half of the sample?\n")
    md.append(f"Across all universes, horizons and scopes, {n_sig} of {n_tests} pattern tests "
              f"({n_sig / n_tests:.1%}) reach |t| > 2; pure chance gives about 4.6%. Each "
              "middle-horizon finding with |t| > 2 is re-run on the first and second half of its "
              "universe's history:\n")
    md.append(markdown(S, ["universe", "pattern", "scope", "split_date", "full_sample_t", "half", "events",
                           "hit_rate", "base_hit_rate", "t"]))
    md.append("")

    md.append("## F. Tradable versions (in context only, stop beyond the pattern bar, 2R target, "
              "time stop 10 days or 8 x 15m bars, after costs)\n")
    md.append("Costs: NSE stock longs 14.5 bps per side (delivery), stock shorts 6 bps (stock futures), "
              "NSE index trades 3.5 bps, global markets per instrument. `ci` is a bootstrap 95% "
              "interval for the mean trade. `random_mean_bps` is the average trade of random entries "
              "with the same holding periods, direction and costs on the same instruments, i.e. what "
              "drift alone pays; `p_random` is the share of random strategies at least as good.\n")
    for u_name in us:
        md.append(f"**{u_name}**\n")
        md.append(markdown(F[F.universe == u_name], ["pattern", "trades", "win_rate", "payoff", "profit_factor",
                                                      "expectancy_bps", "ci_low_bps", "ci_high_bps",
                                                      "random_mean_bps", "p_random"]))
        md.append("")

    md.append("## G. EMA trend + pullback + candle trigger vs control entries\n")
    md.append("Setup: EMA 20 above EMA 50 and close above EMA 50 (mirror for shorts), the bar trades "
              "within 0.5 ATR of the 20 EMA. Trigger: any of engulfing, hammer/shooting star, pin bar, "
              "morning/evening star, piercing/dark cloud. Controls take the same setup without the "
              "candle. Stop beyond the signal bar, 2R target, 20 day (16 x 15m) time stop, after costs.\n")
    md.append(markdown(G, ["universe", "side", "entry", "trades", "win_rate", "payoff", "profit_factor",
                           "expectancy_bps", "ci_low_bps", "ci_high_bps", "random_mean_bps", "p_random"]))
    md.append("")

    # Figure: excess hit rate at the middle horizon, in context, per universe
    fig, axes = plt.subplots(1, len(us), figsize=(14, 6.5), sharey=True)
    order = list(patterns.PATTERNS)
    for ax, (u_name, u) in zip(axes, us.items()):
        h_mid = (INTRA_H if u["kind"] == "intraday" else DAILY_H)[1]
        sub = E[(E.universe == u_name) & (E.scope == "in context")].set_index("pattern").reindex(order)
        excess = (sub[f"hit_rate_{h_mid}"] - sub[f"base_hit_rate_{h_mid}"]) * 100
        sig = sub[f"t_{h_mid}"].abs() > 2
        colors = [SERIES[0] if (s and v > 0) else (SERIES[7] if (s and v < 0) else INK["axis"])
                  for v, s in zip(excess.fillna(0), sig.fillna(False))]
        y = np.arange(len(order))
        ax.barh(y, excess.fillna(0), color=colors, height=0.7)
        ax.axvline(0, color=INK["muted"], lw=0.8)
        ax.set_yticks(y, [o.replace("_", " ") for o in order], fontsize=7)
        unit = "15m bars" if u["kind"] == "intraday" else "days"
        ax.set_title(f"{u_name}\nh = {h_mid} {unit}", fontsize=8.5)
        ax.set_xlabel("hit rate minus base rate, pts")
    axes[0].invert_yaxis()  # shared y axis: invert once, not per panel
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=SERIES[0], label="better than base, |t| > 2"),
                        Patch(color=SERIES[7], label="worse than base, |t| > 2"),
                        Patch(color=INK["axis"], label="not significant")],
               loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Candlestick patterns in context: success percentage relative to bars with the same prior trend",
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(fig_path("E_candles_excess_hit_rate"))
    plt.close(fig)
    md.insert(4, "![candles](figures/E_candles_excess_hit_rate.png)\n")

    with open(os.path.join(ROOT, "results", "candles.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
