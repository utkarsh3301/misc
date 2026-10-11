"""
What does backtrader's default SharpeRatio analyzer actually measure?

backtrader/analyzers/sharpe.py defaults: timeframe=Years, riskfreerate=0.01, stddev_sample=False.
So unless you change it, the "Sharpe" is computed from one return per calendar year.

For 60 CSI300 stocks we run the same buy-and-hold strategy through backtrader over a 3-year and a
9-year window, then compare the default analyzer with a Sharpe computed from daily returns
(SharpeRatio with timeframe=Days, annualize=True) on the very same run. We also check that a
market order placed on bar t fills at the open of bar t+1 (backtrader's default).

Usage: python sharpe_analyzer_check.py /path/to/qlib_data/cn
"""
import sys
import warnings
from pathlib import Path

import backtrader as bt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(sys.argv[1]).expanduser()
cal = pd.to_datetime(pd.read_csv(ROOT / "calendars/day.txt", header=None)[0])


def read(code, f):
    a = np.fromfile(ROOT / "features" / code / f"{f}.day.bin", dtype="<f4")
    return pd.Series(a[1:], index=cal[int(a[0]) : int(a[0]) + len(a) - 1].values).astype("float64")


class BuyHold(bt.Strategy):
    def __init__(self):
        self.fill = None

    def next(self):
        if not self.position and self.fill is None:
            self.order_bar = len(self)
            self.buy(size=int(self.broker.getcash() * 0.95 / self.data.close[0]))

    def notify_order(self, order):
        if order.status == order.Completed:
            self.fill = (order.executed.price, len(self))


def run(df):
    cer = bt.Cerebro(stdstats=False)
    cer.adddata(bt.feeds.PandasData(dataname=df))
    cer.addstrategy(BuyHold)
    cer.broker.setcash(1_000_000)
    cer.addanalyzer(bt.analyzers.SharpeRatio, _name="default")
    cer.addanalyzer(bt.analyzers.SharpeRatio, _name="daily", timeframe=bt.TimeFrame.Days,
                    annualize=True, riskfreerate=0.01)
    s = cer.run()[0]
    fill_price, fill_bar = s.fill
    next_open = df["open"].iloc[s.order_bar]  # bar after the order (0-based index = len at order)
    return (s.analyzers.default.get_analysis()["sharperatio"],
            s.analyzers.daily.get_analysis()["sharperatio"],
            np.isclose(fill_price, next_open))


codes = sorted(p.name for p in (ROOT / "features").iterdir() if p.name.startswith(("sh60", "sz00")))
rng = np.random.default_rng(5)
rows = []
for code in rng.choice(codes, 120, replace=False):
    raw = pd.DataFrame({f: read(code, f) for f in ["open", "high", "low", "close", "volume"]}).dropna()
    for label, start, end in [("3 years 2017-2019", "2017-01-01", "2019-12-31"),
                              ("9 years 2011-2019", "2011-01-01", "2019-12-31")]:
        df = raw.loc[start:end]
        if len(df) < 0.9 * 244 * (int(end[:4]) - int(start[:4]) + 1):
            continue
        try:
            d, y, ok = run(df)
        except Exception:
            continue
        rows.append((code, label, d, y, ok))
    if len({r[0] for r in rows}) >= 60:
        break
t = pd.DataFrame(rows, columns=["code", "window", "default_yearly", "daily_annualised", "fill_at_next_open"]).dropna()
for w, g in t.groupby("window"):
    diff = (g.default_yearly - g.daily_annualised).abs()
    print(f"{w}: {g.code.nunique()} stocks")
    print(f"  median |default - daily| Sharpe gap: {diff.median():.2f}, largest: {diff.max():.2f}")
    print(f"  rank correlation between the two: {g.default_yearly.rank().corr(g.daily_annualised.rank()):.2f}")
    print(f"  share where the default reports a higher Sharpe: {(g.default_yearly > g.daily_annualised).mean():.0%}")
print(f"\nMarket order filled at the next bar's open in {t.fill_at_next_open.mean():.0%} of runs")
print("\nLargest gaps:")
t["gap"] = (t.default_yearly - t.daily_annualised).abs()
print(t.nlargest(4, "gap")[["code", "window", "default_yearly", "daily_annualised"]].to_string(index=False, float_format=lambda x: f"{x:+.2f}"))
