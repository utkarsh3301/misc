# 01. Microsoft qlib (Alpha158 + LightGBM)

Repo: https://github.com/microsoft/qlib
Studied: shallow clone of `main`, October 2026.

## What it is

qlib is Microsoft's research platform for cross-sectional stock selection. You give it daily
price data, it builds hundreds of features per stock per day, trains a model to rank stocks by
expected return, and backtests a long-only portfolio of the top-ranked names. Its benchmark
tables (CSI300 and CSI500, China A-shares) are the most cited reference point for "ML stock
picking" in open source.

## How it works (from the source)

| Piece | File | What it actually does |
|---|---|---|
| Features | `qlib/contrib/data/loader.py` (`Alpha158DL.get_feature_config`) | 158 hand-written formulas: candle shape (KMID, KSFT...), price relative to past prices (ROC, MA), volatility, highs/lows, up-day counts, price-volume correlation, volume ratios. Windows of 5, 10, 20, 30, 60 days. Every price feature is divided by today's close, so it is unitless. |
| Label | `qlib/contrib/data/handler.py` | `Ref($close, -2)/Ref($close, -1) - 1`: the return from tomorrow's close to the day after. Nothing from today's trading leaks in. |
| Label cleaning | `_DEFAULT_LEARN_PROCESSORS` | Labels are z-scored across stocks each day (`CSZScoreNorm`). The model learns "better or worse than other stocks today", not "up or down". |
| Model | `examples/benchmarks/LightGBM/*.yaml` | Gradient boosted trees, very heavy L1/L2 regularisation (205 and 581), trained 2008-2014, early stopped on 2015-2016, tested 2017 to mid 2020. |
| Portfolio | `qlib/contrib/strategy/signal_strategy.py` (`TopkDropoutStrategy`) | Hold 50 stocks. Each day sell the 5 worst-ranked holdings and buy the 5 best-ranked non-holdings. Signal from day t is traded on day t+1 (`shift=1`), at the close. |
| Costs | same yaml | 5 bp to buy, 15 bp to sell (the 10 bp extra is China's stamp duty), stocks at the 9.5% price limit cannot be traded. |

The plumbing is clean. I found no look-ahead in the label, the signal timing, or the backtest.

## Where the edge is supposed to come from

The pitch is "better models find more alpha". The benchmark table lists ~20 models, from Linear
to Transformers and graph networks.

## What I found

**1. The model barely matters. The features and the market do.** In qlib's own CSI300
Alpha158 table, a plain linear model gets IC 0.040. Of the 18 models listed, 11 score below it,
including every recurrent, attention and Transformer-style network (Transformer 0.026, TabNet
0.020). The top four are all tree ensembles; the best (DoubleEnsemble, IC 0.052) is bagged
LightGBM.

**2. The signal is mostly short-term reversal in China A-shares.** I rebuilt 19 of the
Alpha158 formulas straight from the code and measured each one alone against qlib's label on
real CSI300 data (point-in-time index membership, 2008 to 2020):

| Feature | What it measures | Rank IC 2008-2020 | Rank IC 2017-2020 |
|---|---|---|---|
| ROC5 | price 5 days ago / price today | +0.047 | +0.027 |
| MA5 | 5-day average / price today | +0.044 | +0.025 |
| KSFT | where today closed inside today's range | -0.034 | -0.013 |
| KMID | today's candle body | -0.032 | -0.015 |
| STD20 | 20-day volatility | -0.003 | +0.000 |

Read it as: stocks that fell over the last week, or closed weak today, tend to beat other
stocks over the next day. That is the classic retail-driven reversal effect in A-shares. The
top features in the trained LightGBM (by gain) are the same ones: ROC5, KSFT, MA5, ROC60, KMID.

**3. A model on those 19 features reaches most of qlib's headline number.** LightGBM on my 19
features: test rank IC 0.038 (qlib's 158-feature LightGBM reports 0.047). The decile spread is
clean and monotonic, from -7.7 bp/day for the worst-ranked tenth to +10.7 bp/day for the best.

**4. The single best feature loses money in qlib's portfolio rule.** ROC5 alone, run through
TopK50/Drop5, lost about 12% a year versus the universe, even though its top decile is
positive. The likely mechanism: Dropout sells the 5 holdings whose score fell most, which for a
reversal signal are the ones that already bounced. What stays in the book are the losers that
kept losing. The portfolio rule and the signal speed have to match; the combined model hides
this because its score is smoother.

**5. Price limits and costs take a big bite.** My rough TopK50/Drop5 replica on the LightGBM
signal, excess return over the equal-weight universe, 2017-01 to 2020-07:

| Setting | Annual excess | Info ratio |
|---|---|---|
| No price-limit rule, qlib costs | +17.0% | 0.81 |
| Respect 9.5% limits, qlib costs | +11.2% | 0.54 |
| Respect limits, costs doubled | +7.2% | 0.35 |

About 10% of the book turns over every day, so costs alone are roughly 5% a year. Ignoring
the limit rule overstates returns by about 6 points a year, because a reversal strategy wants
to buy exactly the stocks that are locked limit-down.

**6. The edge is decaying.** Rank IC of the same trained model by year: 2017 0.058, 2018
0.036, 2019 0.019, 2020 0.027. On the 10 months after qlib's benchmark window (2020-08 to
2021-05), which the benchmark never touched, it is 0.021.

**7. A copy-paste error in the benchmark tables.** In `examples/benchmarks/README.md`, the
CSI500 rows for DoubleEnsemble (both Alpha158 and Alpha360) carry exactly the same backtest
numbers as the CSI500 Linear row: annual return 0.0382, information ratio 0.1723, max
drawdown -0.4876. Those three numbers cannot all be identical by chance, so the DoubleEnsemble
CSI500 backtest results are not real measurements.

## The edge, in one line

A carefully engineered short-horizon reversal and price-volume signal on China A-shares,
extracted with a well-regularised tree model and traded with tight turnover control. Real, but
thin after costs and limits, and shrinking since 2017. The fancy models add little.

## Takeaways for our own work

- Start with the feature formulas, not the model zoo. A linear model is a strong baseline.
- Any reversal strategy in a market with price bands (India has them too: 2%, 5%, 10%, 20%
  bands on many stocks) must refuse fills at the band, or the backtest is fiction.
- Match the portfolio rule to the signal's half-life before blaming the signal.
- Always hold back a period that no one, including the benchmark authors, has looked at.

## Reproduce

```
# data: qlib's public CN daily set (about 50 MB)
curl -L -o cn.zip https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_simple_cn_1d_latest.zip
unzip cn.zip -d cn
pip install lightgbm pandas numpy
python experiments/alpha158_probe.py ./cn
```

The script reads qlib's `.bin` files directly, so qlib itself does not need to be installed.
My backtest is a simplified replica of TopkDropoutStrategy (equal weights, excess over the
equal-weight universe rather than the cap-weighted index), so absolute numbers differ from
qlib's tables. The comparisons between settings are the point.
