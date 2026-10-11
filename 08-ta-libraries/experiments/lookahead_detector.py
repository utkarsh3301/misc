"""
Automatic look-ahead test for technical-indicator libraries.

Idea: an indicator value for day t must not change when you delete every bar after t.
For each indicator we compute it once on the full history, then again on the history cut at
40 random dates, and compare the value on the cut date. Any difference means the value on
day t depended on bars after t.

Truncating only at the end means warm-up effects (an EMA that depends on where the series
starts) cannot trigger a false alarm.

Libraries tested:
  ta        https://github.com/bukosabino/ta   (add_all_ta_features)
  pandas-ta https://github.com/twopirllc/pandas-ta (every indicator in df.ta.indicators())

Usage: python lookahead_detector.py /path/to/qlib_data/cn
       (put a clone of bukosabino/ta on PYTHONPATH if `pip install ta` fails)
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(sys.argv[1]).expanduser()
cal = pd.to_datetime(pd.read_csv(ROOT / "calendars/day.txt", header=None)[0])


def read(code, f):
    a = np.fromfile(ROOT / "features" / code / f"{f}.day.bin", dtype="<f4")
    return pd.Series(a[1:], index=cal[int(a[0]) : int(a[0]) + len(a) - 1].values).astype("float64")


df = pd.DataFrame({f: read("sh600000", f) for f in ["open", "high", "low", "close", "volume"]})
df = df.loc["2012-01-01":"2020-12-31"].dropna()
rng = np.random.default_rng(1)
cuts = sorted(rng.choice(np.arange(300, len(df) - 40), size=40, replace=False))


def leaks(full: pd.DataFrame, compute) -> dict:
    """For each column, the share of cut dates where the truncated value differs from the full one."""
    bad = {c: 0 for c in full.columns}
    seen = {c: 0 for c in full.columns}
    for k in cuts:
        part = compute(df.iloc[: k + 1])
        if part is None:
            continue
        last = part.iloc[-1]
        ref = full.iloc[k]
        for c in full.columns:
            if c not in last.index:
                continue
            a, b = ref[c], last[c]
            if pd.isna(a) and pd.isna(b):
                continue
            seen[c] += 1
            if pd.isna(a) != pd.isna(b) or not np.isclose(a, b, rtol=1e-6, atol=1e-9):
                bad[c] += 1
    return {c: bad[c] / seen[c] for c in full.columns if seen[c] and bad[c]}


# ---------- ta ----------
import ta  # noqa: E402


def ta_all(d):
    out = ta.add_all_ta_features(d.copy(), open="open", high="high", low="low", close="close",
                                 volume="volume", fillna=False)
    return out.drop(columns=["open", "high", "low", "close", "volume"])


full_ta = ta_all(df)
ta_bad = leaks(full_ta, ta_all)
print(f"ta: {full_ta.shape[1]} indicator columns tested, {len(ta_bad)} use future bars")
for c, r in sorted(ta_bad.items()):
    print(f"  {c:32s} changed on {r:.0%} of cut dates")

# ---------- pandas-ta ----------
import pandas_ta  # noqa: E402,F401

names = [n for n in df.ta.indicators(as_list=True)]
pta_bad, tested, failed = {}, 0, 0
for n in names:
    def comp(d, n=n):
        try:
            r = getattr(d.ta, n)()
        except Exception:
            return None
        if r is None:
            return None
        return r.to_frame() if isinstance(r, pd.Series) else r

    full = comp(df)
    if full is None or len(full) != len(df):
        failed += 1
        continue
    full = full.select_dtypes("number")
    if full.empty:
        failed += 1
        continue
    tested += 1
    b = leaks(full, lambda d, n=n: (lambda x: None if x is None else x.select_dtypes("number"))(comp(d)))
    if b:
        pta_bad[n] = b
print(f"\npandas-ta: {tested} indicators tested ({failed} skipped: errors or non-aligned output), "
      f"{len(pta_bad)} use future bars")
for n, cols in sorted(pta_bad.items()):
    worst = max(cols.items(), key=lambda kv: kv[1])
    print(f"  {n:12s} {len(cols)} column(s), e.g. {worst[0]} changed on {worst[1]:.0%} of cut dates")

# Documented "safe" modes for the leaking pandas-ta indicators
print("\npandas-ta safe modes:")
for label, fn in [
    ("dpo(centered=False)", lambda d: d.ta.dpo(centered=False).to_frame()),
    ("zigzag(backtest=True)", lambda d: d.ta.zigzag(backtest=True)),
    ("ichimoku() default", lambda d: d.ta.ichimoku()[0]),
    ("ichimoku(lookahead=False)", lambda d: d.ta.ichimoku(lookahead=False)[0]),
]:
    try:
        full = fn(df).select_dtypes("number")
        b = leaks(full, lambda d, fn=fn: fn(d).select_dtypes("number"))
        print(f"  {label:26s} " + (f"still uses future bars (worst column changed on {max(b.values()):.0%} of cut dates)" if b else "clean"))
    except Exception as e:
        print(f"  {label:24s} could not run: {type(e).__name__}")

# zigzag(backtest=True) with one extra bar of shift
print("\nzigzag(backtest=True), library shift vs one extra bar:")
for extra in (0, 1):
    fn = lambda d, e=extra: d.ta.zigzag(backtest=True).shift(e)
    b = leaks(fn(df).select_dtypes("number"), lambda d: fn(d).select_dtypes("number"))
    print(f"  extra shift {extra}: " + ("uses future bars" if b else "clean"))
