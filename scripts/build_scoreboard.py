"""
Builds the headline "success percentage" scoreboards in
results/scoreboard.md from the CSV tables the experiment scripts write.
Run after run_ema_daily.py, run_ema_intraday.py and run_candles.py.

Usage: python scripts/build_scoreboard.py
"""

import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = os.path.join(ROOT, "results", "tables")


def t(name):
    return pd.read_csv(os.path.join(TABLES, f"{name}.csv"))


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def ema_scoreboard():
    a1, a3, b1, b2, c1 = t("A1_index_classic_pairs"), t("A3_index_variants"), t("B1_stock_results"), \
        t("B2_stock_portfolios"), t("C1_global")
    d1, d3 = t("D1_intraday_grid"), t("D3_fixed_point_scalper")
    rows = []

    def add(strategy, market, r, bh=True, trades=None):
        avg = f"{r.expectancy * 100:+.2f}%" if bh else f"{r.expectancy * 1e4:+.1f} bps"
        rows.append([strategy, market, str(int(trades if trades is not None else r.trades)), pct(r.win_rate),
                     f"{r.profit_factor:.2f}", avg, pct(r.cagr), pct(r.max_dd, 0),
                     f"{pct(r.bh_cagr)} / {pct(r.bh_max_dd, 0)}" if bh else "n/a"])

    def pick(df, **kw):
        m = pd.Series(True, index=df.index)
        for k, v in kw.items():
            m &= df[k] == v
        return df[m].iloc[0]

    add("EMA 20/50 long only, daily", "NIFTY 2007-2026", pick(a1, market="NIFTY", rule="EMA 20/50", side="long_only"))
    add("EMA 9/21 long only, daily", "NIFTY 2007-2026", pick(a1, market="NIFTY", rule="EMA 9/21", side="long_only"))
    add("EMA 50/200 long only, daily", "NIFTY 2007-2026", pick(a1, market="NIFTY", rule="EMA 50/200", side="long_only"))
    add("EMA 20/50 long/short, daily", "NIFTY 2007-2026", pick(a1, market="NIFTY", rule="EMA 20/50", side="long_short"))
    add("Close above EMA 50, daily", "NIFTY 2007-2026", pick(a3, market="NIFTY", rule="Close > EMA 50"))
    add("EMA 20/50 + 3 ATR trailing stop", "NIFTY 2007-2026", pick(a3, market="NIFTY", rule="EMA 20/50 + 3 ATR trailing stop"))
    add("EMA 12/26 long only, daily", "BANKNIFTY 2010-2026", pick(a1, market="BANKNIFTY", rule="EMA 12/26", side="long_only"))
    add("EMA 20/50 long only, daily", "BANKNIFTY 2010-2026", pick(a1, market="BANKNIFTY", rule="EMA 20/50", side="long_only"))

    s = b1[b1.rule == "EMA 20/50"]
    port = b2.set_index("portfolio")
    rows.append(["EMA 20/50 long only, daily", "62 NSE stocks 2005-2026, equal weight",
                 str(int(s.trades.sum())), pct(s.win_rate.mean()), f"{s.profit_factor.median():.2f} (median)",
                 f"{s.expectancy.mean() * 100:+.2f}%", pct(port.loc["EMA 20/50", "cagr"]),
                 pct(port.loc["EMA 20/50", "max_dd"], 0),
                 f"{pct(port.loc['Buy and hold', 'cagr'])} / {pct(port.loc['Buy and hold', 'max_dd'], 0)}"])

    d = c1[c1.bars == "1d"]
    add("EMA 20/50 long only, daily", "S&P 500 CFD 2005-2020", pick(d, market="SPX500_USD", rule="EMA 20/50", side="long_only"))
    add("EMA 50/200 long only, daily", "Gold 2006-2020", pick(d, market="XAU_USD", rule="EMA 50/200", side="long_only"))
    add("EMA 20/50 long/short, daily", "EUR/USD 2005-2020", pick(d, market="EUR_USD", rule="EMA 20/50", side="long_short"))

    for tf, rule, costs in [("5m", "EMA 9/21", "gross"), ("5m", "EMA 9/21", "2026 costs"),
                            ("15m", "EMA 20/50", "gross"), ("15m", "EMA 20/50", "2026 costs")]:
        r = pick(d1, market="NIFTY", timeframe=tf, rule=rule, costs=costs)
        add(f"{rule} long/short, {tf} intraday, {costs}", "NIFTY 2011-2023", r, bh=False)

    for costs in ["gross", "futures 2026"]:
        r = pick(d3, market="NIFTY", **{"target/stop pts": "8/5", "costs": costs})
        rows.append([f"Original 1m 9/21 scalper, +8/-5 pts, {costs}", "NIFTY 2011-2023", str(int(r.trades)),
                     pct(r.win_rate), f"{r.profit_factor:.2f}", f"{r.expectancy_pts:+.2f} pts", "n/a", "n/a", "n/a"])

    head = ["Strategy", "Market and period", "Trades", "Success % (win rate)", "Profit factor", "Avg trade",
            "CAGR", "Max DD", "Buy and hold CAGR / Max DD"]
    return head, rows


def candle_scoreboard():
    e, f = t("E_candles_event_study"), t("F_candles_tradable")
    rows = []
    for u, h in [("NSE stocks (daily)", 5), ("NIFTY/BANKNIFTY (15m)", 4)]:
        for p in ["bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "morning_star",
                  "evening_star", "bullish_pin_bar", "bearish_pin_bar", "inside_bar_breakout_up"]:
            ev = e[(e.universe == u) & (e.pattern == p) & (e.scope == "in context")].iloc[0]
            tr = f[(f.universe == u) & (f.pattern == p)].iloc[0]
            unit = f"{h} x 15m" if "15m" in u else f"{h} days"
            rows.append([p.replace("_", " "), u, str(int(ev.events)), f"{pct(ev[f'hit_rate_{h}'])} ({unit})",
                         pct(ev[f"base_hit_rate_{h}"]), f"{ev[f't_{h}']:.2f}", str(int(tr.trades)), pct(tr.win_rate),
                         f"{tr.expectancy_bps:+.0f} bps", f"{tr.random_mean_bps:+.0f} bps"])
    head = ["Pattern (in context)", "Universe", "Events", "Success %", "Base rate", "t (mean excess)",
            "Trades", "Win rate after costs", "Avg trade after costs", "Random entry avg"]
    return head, rows


def md(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def main():
    h1, r1 = ema_scoreboard()
    h2, r2 = candle_scoreboard()
    text = ["# Scoreboards\n", "Generated by `scripts/build_scoreboard.py` from `results/tables`.\n",
            "## EMA strategies (after costs unless marked gross)\n", md(h1, r1), "",
            "## Candlestick patterns\n",
            "Success % is the share of occurrences followed by a move in the predicted direction from the "
            "next open to the close h bars later; base rate is the same for every bar with the same prior "
            "trend. Win rate and average trade are for the tradable version (stop beyond the pattern bar, "
            "2R target, time stop) after costs; random entry avg is what random entries with the same "
            "holding periods earned.\n", md(h2, r2), ""]
    path = os.path.join(ROOT, "results", "scoreboard.md")
    with open(path, "w") as f:
        f.write("\n".join(text) + "\n")
    print("\n".join(text))


if __name__ == "__main__":
    main()
