"""
Probe where qlib's Alpha158 + LightGBM edge comes from.

Reads qlib's public CN daily dataset directly from its .bin files (no qlib install),
rebuilds a subset of Alpha158 features with the same formulas, and measures:
  1. daily rank IC of each single feature vs qlib's label
  2. rank IC of a LightGBM model on those features (same train/valid/test split as qlib's benchmark)
  3. a rough TopK-Dropout style long-only backtest with qlib's cost settings

Usage: python alpha158_probe.py /path/to/qlib_data/cn
Data: https://github.com/SunsetWolf/qlib_dataset/releases (v2/qlib_data_simple_cn_1d_latest.zip)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "~/.qlib/qlib_data/cn_data").expanduser()
FIELDS = ["open", "high", "low", "close", "volume"]

cal = pd.to_datetime(pd.read_csv(ROOT / "calendars/day.txt", header=None)[0])
spans = pd.read_csv(ROOT / "instruments/csi300.txt", sep="\t", header=None, names=["code", "start", "end"])
spans["start"] = pd.to_datetime(spans["start"])
spans["end"] = pd.to_datetime(spans["end"])


def read_bin(code, field):
    p = ROOT / "features" / code.lower() / f"{field}.day.bin"
    if not p.exists():
        return None
    a = np.fromfile(p, dtype="<f4")
    start = int(a[0])
    return pd.Series(a[1:], index=cal[start : start + len(a) - 1].values)


panel = {f: {} for f in FIELDS}
for code in spans["code"].unique():
    for f in FIELDS:
        s = read_bin(code, f)
        if s is not None:
            panel[f][code] = s
P = {f: pd.DataFrame(v).sort_index() for f, v in panel.items()}
o, h, l, c, v = (P[f] for f in FIELDS)

# Point-in-time index membership (avoids survivorship bias)
member = pd.DataFrame(False, index=c.index, columns=c.columns)
for _, r in spans.iterrows():
    if r.code in member.columns:
        member.loc[(member.index >= r.start) & (member.index <= r.end), r.code] = True

# qlib label: return from close(t+1) to close(t+2)
label = c.shift(-2) / c.shift(-1) - 1

ret1 = c / c.shift(1)
feats = {
    # kbar
    "KMID": (c - o) / o,
    "KLEN": (h - l) / o,
    "KSFT": (2 * c - h - l) / o,
    # rolling, a representative slice of Alpha158
    "ROC5": c.shift(5) / c,
    "ROC20": c.shift(20) / c,
    "ROC60": c.shift(60) / c,
    "MA5": c.rolling(5).mean() / c,
    "MA20": c.rolling(20).mean() / c,
    "STD5": c.rolling(5).std() / c,
    "STD20": c.rolling(20).std() / c,
    "MAX20": h.rolling(20).max() / c,
    "MIN20": l.rolling(20).min() / c,
    "RSV20": (c - l.rolling(20).min()) / (h.rolling(20).max() - l.rolling(20).min() + 1e-12),
    "CNTD20": (c > c.shift(1)).astype(float).rolling(20).mean() - (c < c.shift(1)).astype(float).rolling(20).mean(),
    "CORR20": c.rolling(20).corr(np.log(v + 1)),
    "CORD20": ret1.rolling(20).corr(np.log(v / v.shift(1) + 1)),
    "VMA20": v.rolling(20).mean() / (v + 1e-12),
    "VSTD20": v.rolling(20).std() / (v + 1e-12),
    "WVMA20": (ret1 - 1).abs().mul(v).rolling(20).std() / ((ret1 - 1).abs().mul(v).rolling(20).mean() + 1e-12),
}


def stack(df):
    return df.where(member).stack()


data = pd.DataFrame({k: stack(f) for k, f in feats.items()})
data["label"] = stack(label)
data = data.replace([np.inf, -np.inf], np.nan).dropna()
data.index.names = ["date", "code"]
data = data.loc["2008-01-01":"2020-08-01"]


def daily_rank_ic(x, y):
    df = pd.DataFrame({"x": x, "y": y})
    ic = df.groupby(level="date").apply(lambda g: g["x"].rank().corr(g["y"].rank()))
    return ic


test = data.loc["2017-01-01":]
rows = []
for k in feats:
    ic_all = daily_rank_ic(data[k], data["label"])
    ic_te = daily_rank_ic(test[k], test["label"])
    rows.append((k, ic_all.mean(), ic_all.mean() / ic_all.std(), ic_te.mean()))
single = pd.DataFrame(rows, columns=["feature", "rankIC_2008_2020", "rankICIR", "rankIC_test_2017_2020"])
single = single.reindex(single["rankIC_2008_2020"].abs().sort_values(ascending=False).index)
print("\nSingle-feature rank IC (sign shows direction):")
print(single.to_string(index=False, float_format=lambda x: f"{x:+.4f}"))

# LightGBM with qlib-style label normalisation (cross-sectional z-score)
import lightgbm as lgb

X = data[list(feats)]
y = data["label"].groupby(level="date").transform(lambda s: (s - s.mean()) / (s.std() + 1e-12))
tr, va, te = (slice("2008-01-01", "2014-12-31"), slice("2015-01-01", "2016-12-31"), slice("2017-01-01", "2020-08-01"))
model = lgb.train(
    dict(objective="regression", learning_rate=0.05, num_leaves=63, max_depth=8, subsample=0.88,
         subsample_freq=1, colsample_bytree=0.89, lambda_l1=205.7, lambda_l2=581.0, verbose=-1, seed=0),
    lgb.Dataset(X.loc[tr], y.loc[tr]),
    num_boost_round=1000,
    valid_sets=[lgb.Dataset(X.loc[va], y.loc[va])],
    callbacks=[lgb.early_stopping(50, verbose=False)],
)
pred = pd.Series(model.predict(X.loc[te]), index=X.loc[te].index)
ic_model = daily_rank_ic(pred, data.loc[te, "label"])
print(f"\nLightGBM on {len(feats)} features, test 2017-2020: rankIC {ic_model.mean():+.4f}, rankICIR {ic_model.mean()/ic_model.std():.3f}")
imp = pd.Series(model.feature_importance("gain"), index=list(feats)).sort_values(ascending=False)
print("Top features by gain:", ", ".join(f"{k} {v/imp.sum():.0%}" for k, v in imp.head(6).items()))

# Rough TopK-Dropout: hold 50, swap worst 5 for best 5 each day, costs 5bp buy / 15bp sell.
# Trades happen at close of t+1 (as in qlib). With respect_limits=True, a stock that closes
# limit-up (>= +9.5%) on the trade day cannot be bought and one that closes limit-down cannot be sold.
lab = data.loc[te, "label"]
trade_day_ret = stack(c.shift(-1) / c - 1).loc[lab.index]


def topk_dropout(score, topk=50, n_drop=5, cost_mult=1.0, respect_limits=False):
    dates = score.index.get_level_values(0).unique()
    held, pnl = [], []
    for d in dates:
        s = score.loc[d].sort_values(ascending=False)
        tr = trade_day_ret.loc[d]
        can_buy = tr < 0.095 if respect_limits else tr == tr
        can_sell = tr > -0.095 if respect_limits else tr == tr
        if not held:
            buys = [x for x in s.index if can_buy.get(x, False)][:topk]
            sells, held = [], buys
        else:
            held = [x for x in held if x in s.index]
            ranked = s.reindex(held).sort_values()
            sells = [x for x in ranked.index if can_sell.get(x, False)][:n_drop]
            buys = [x for x in s.index if x not in held and can_buy.get(x, False)][: len(sells)]
            held = [x for x in held if x not in sells] + buys
        r = lab.loc[d].reindex(held).mean() - lab.loc[d].mean()
        cost = cost_mult * (len(buys) * 0.0005 + len(sells) * 0.0015) / topk
        pnl.append(r - cost)
    pnl = pd.Series(pnl, index=dates)
    return pnl.mean() * 252, pnl.mean() / pnl.std() * np.sqrt(252), pnl


print("\nTopK50/Drop5 long-only, excess vs equal-weight CSI300 members, test 2017-01 to 2020-07:")
roc5 = data.loc[te, "ROC5"]
for name, sc in [("LightGBM (19 feats)", pred), ("ROC5 alone (buy 5-day losers)", roc5)]:
    for lim in (False, True):
        for cm in (1.0, 2.0):
            a, ir, _ = topk_dropout(sc, cost_mult=cm, respect_limits=lim)
            print(f"  {name:32s} limits={'on ' if lim else 'off'} costs x{cm:.0f}: ann {a:+.1%}, IR {ir:.2f}")

# Why can a feature with positive IC lose money as a top-50 portfolio? Look at the deciles.
print("\nMean next-period return (bp/day, vs cross-section mean) by decile, test period:")
for name, sc in [("ROC5", roc5), ("LightGBM", pred)]:
    df = pd.DataFrame({"s": sc, "y": lab})
    df["y"] = df["y"] - df.groupby(level="date")["y"].transform("mean")
    df["dec"] = df.groupby(level="date")["s"].transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=False))
    m = df.groupby("dec")["y"].mean() * 1e4
    print(f"  {name:9s} " + " ".join(f"{x:+6.1f}" for x in m.values) + "   (decile 0 = lowest score, 9 = highest)")

# Does the edge survive after qlib's benchmark window? Same model, untouched period 2020-08 to 2021-05.
post = slice("2020-08-02", "2021-05-31")
data_post = pd.DataFrame({k: stack(f) for k, f in feats.items()})
data_post["label"] = stack(label)
data_post = data_post.replace([np.inf, -np.inf], np.nan).dropna()
data_post.index.names = ["date", "code"]
data_post = data_post.loc[post]
pred_post = pd.Series(model.predict(data_post[list(feats)]), index=data_post.index)
ic_post = daily_rank_ic(pred_post, data_post["label"])
print(f"\nAfter the benchmark window (2020-08 to 2021-05): rankIC {ic_post.mean():+.4f}, rankICIR {ic_post.mean()/ic_post.std():.3f}, days {len(ic_post)}")
print("Rank IC by year (test + post):", ", ".join(
    f"{y}: {v:+.3f}" for y, v in pd.concat([ic_model, ic_post]).groupby(lambda d: d.year).mean().items()))
