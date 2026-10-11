# 08. Technical-indicator libraries: ta, pandas-ta and stockstats

Repos: https://github.com/bukosabino/ta (clone of `master`, last commit March 2026) and the
`pandas-ta` package from PyPI, version 0.4.71b0 (project: https://github.com/twopirllc/pandas-ta),
plus `stockstats` 0.6.9 from PyPI (project: https://github.com/jealous/stockstats), the library
TradingAgents uses.

## Why these

Almost every strategy in folders 01 to 07 starts from indicators like these, and most retail
and many professional Python backtests import one of these libraries. If an indicator
quietly uses future bars, every strategy built on it inherits a look-ahead nobody wrote.

## How I tested them: an automatic look-ahead detector

A value for day t must not change when you delete every bar after t. So for each indicator:

1. compute it once on the full 2012 to 2020 history of one stock (SPD Bank, sh600000)
2. cut the history at 40 random dates and recompute on each truncated history
3. compare the value on the cut date with the full-history value for that date

Any difference means the indicator used bars after t. Cutting only at the end means an EMA that
depends on where the series starts cannot cause a false alarm. The detector is generic: point it
at any feature function, including your own.

## Results

**ta (bukosabino): clean.** All 86 indicator columns from `add_all_ta_features` passed. Its
Detrended Price Oscillator is the trailing version (`close.shift(n/2 + 1) - SMA(n)`), which is
the safe choice.

**pandas-ta: 4 of 153 indicators use future bars with default settings, plus Ichimoku.**

| Indicator | What goes wrong | Changed on cut dates | Safe setting |
|---|---|---|---|
| `dpo` | Default `centered=True` shifts the result back by `length/2 + 1` bars, so today's value uses the next ~11 closes. The docstring admits it: "Set centered=False to remove data leakage." | 100% | `centered=False` (passes) |
| `ichimoku` | Default `lookahead=True` includes the chikou span, which is the close shifted back 26 bars. | 100% | `lookahead=False` (passes) |
| `tos_stdevall` | Fits one linear regression and one standard deviation over the whole series, so every past value depends on all future data. | 100% | none: only valid on data up to today |
| `vhm` | `from statistics import pstdev`, then `pstdev(volume, std_length)`. Python's `pstdev(data, mu)` takes the mean as its second argument, not a window. So it computes the standard deviation of the entire volume history, and on the Python 3.13 used here it measures it around a "mean" of 610. A look-ahead and a wrong formula at once. | 100% | none: needs a fix to a rolling std |
| `zigzag` | Pivots need bars on both sides, so the default output is placed on the pivot bar, before it could be known. | 100% | `backtest=True` is meant to fix this but is one bar short (see below) |

**The zigzag "backtest mode" is off by one bar.** With `backtest=True` the output is shifted by
`floor(legs/2)` bars. But the pivot search loop (`nb_rolling_hl`, `range(left, m - right)` with
`right = left + 1`) needs one more bar than that. Run through the detector, the library's shift still leaks;
shifting the result one extra bar passes cleanly. So a strategy
using `zigzag(backtest=True)` still sees each swing point one bar early.

**stockstats 0.6.9 (used by TradingAgents): clean, with one sharp edge.** The 13 indicators
TradingAgents' market analyst requests (SMA 50/200, EMA 10, MACD and signal and histogram, RSI,
Bollinger bands, ATR, VWMA, MFI) and 40 other stockstats indicators all pass. The one failure is
by design: in stockstats column names, a negative offset reads the past and a positive offset reads
the future (the source says so: "positive values meaning data in the future"). `close_-2_r` is a
feature, `close_2_r` is a peek, and the detector flags the second on 39 of 40 cut dates. One
missing minus sign is all it takes.

## The edge, in one line

These are tools, not strategies, so there is no edge to find. But a leaking indicator manufactures
a fake one: anything built on centered DPO, default Ichimoku, VHM, TOS StDevAll or zigzag will
backtest better than it can trade.

## Takeaways for our own work

- Run the truncation test on every feature before it goes into a model. It costs seconds and
  catches leaks that no code review will.
- Prefer `ta` for standard indicators, or pin pandas-ta and pass the safe settings explicitly
  (`dpo(centered=False)`, `ichimoku(lookahead=False)`); never use `vhm`, `tos_stdevall` or
  `zigzag` in a backtest without fixing them.
- "Backtest mode" flags in libraries need testing too, not trusting.
- With stockstats-style column names, lint for positive offsets before anything reaches a model.

## Reproduce

```
curl -L -o cn.zip https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_simple_cn_1d_latest.zip
unzip cn.zip -d cn
pip install pandas-ta ta
python experiments/lookahead_detector.py ./cn
pip install stockstats
python experiments/stockstats_check.py ./cn
```

If `pip install ta` fails to build, clone https://github.com/bukosabino/ta and put the clone on
`PYTHONPATH`; it is pure Python. TA-Lib candle patterns in pandas-ta are skipped when TA-Lib is
not installed.
