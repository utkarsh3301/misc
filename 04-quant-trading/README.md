# 04. je-suis-tm/quant-trading (classic technical and stat-arb strategies)

Repo: https://github.com/je-suis-tm/quant-trading
Studied: shallow clone of `master`, October 2026.

## What it is

One of the most starred collections of trading strategy scripts on GitHub: MACD, Heikin-Ashi,
Dual Thrust, London Breakout, Parabolic SAR, RSI and Bollinger pattern recognition, pairs
trading, an options straddle and several "quantamental" projects. Each script downloads data,
generates signals, plots them, and for some strategies computes a portfolio and statistics.

## How the backtests work (from the source)

Most scripts share one pattern:

```
signals['positions'] = rule(prices)              # 1 = long, 0 = flat
signals['signals']   = positions.diff()          # entries and exits
portfolio['holdings'] = cumsum(signals) * Close * shares
portfolio['cash']     = capital - cumsum(signals * Close * shares)
```

So every trade fills at the same Close that produced the signal, and there are no costs. A few
scripts only plot signals and never compute PnL (MACD, for example).

## Where the edge is supposed to come from

Each strategy claims a classic market anomaly: trend following (MACD), candle-pattern reversal
(Heikin-Ashi), opening-range breakout (Dual Thrust, London Breakout), or mean reversion of a
cointegrated spread (pairs trading).

## What I found

### Code findings

**1. Dual Thrust uses the current session's high and low to set that session's entry bands.**
`min2day` builds a daily table from the 3:00 to 12:00 session and computes
`range = rolling(rg)` of highs, lows and closes. In `signal_generation`, at 3:00 on date D the
bands are `open + k * intraday['range'][date]`. That row of the rolling window includes day D
itself, whose high and low have not happened yet at 3:00. Fix: shift the range by one day.

For contrast, the Dual Thrust template in vnpy (https://github.com/vnpy/vnpy_ctastrategy,
`strategies/dual_thrust_strategy.py`) computes the range from the previous day's high and low at
the first bar of the new day, and vnpy's backtester fills a stop order on the next bar at
`max(stop price, bar open)`, so a gap through the stop is charged at the worse open. That is
what an honest version looks like.

**2. Pairs trading mixes units in its entry bands.** When a pair becomes cointegrated, the
bands are set as `z_upper = z_now + std(residual)` and `z_lower = z_now - std(residual)`.
`z` is a unitless z-score, `std(residual)` is in price units. So the band width depends on
whether you quote in rupees or paise. The bands are also centred on today's z, not on zero.

**3. Pairs trading sizes positions with the future.** `portfolio()` sets
`positions1 = capital0 // max(data['asset1'])`: the maximum price over the entire backtest,
including prices that have not happened yet.

**4. Pairs trading silently stops trading on modern pandas.** It writes results through
chained assignment (`signals['z'].iloc[i:] = ...`). Under pandas 3 copy-on-write those writes
are dropped without an error, so `z` stays empty and the strategy never enters a trade.

**5. The options straddle undercounts its own premium by 10x and picks the strike after
expiry.** `straddle()` multiplies spot by the contract size (10 EUR per STOXX 50 point) and the
profit line multiplies the strike too, but the call and put premiums, also quoted in index
points, are left unscaled. `main()` then loops over every strike, and the comments describe
picking "the optimal strike price to maximize our profit", which can only be known at expiry.
The entry rule (buy when call and put prices are within 2 points) says nothing about whether
volatility is cheap, which is the only reason to own a straddle.

Re-running it on the repo's own data (August 2019 expiry):

| Strike | Entry | Premium (points) | PnL as the repo computes it | PnL with premium in EUR |
|---|---|---|---|---|
| 3350 | 2019-04-03 | 224.4 | -15 | -2,035 |
| 3375 | 2019-06-10 | 158.3 | +301 | -1,124 |
| 3450 | 2019-06-21 | 133.7 | +1,076 | -128 |

Two of three trades look profitable as written. With consistent units, none are.

### Experiments on real data (about 300 CSI300 stocks, 2008 to 2021)

**Pairs trading is not unit invariant.** Running the repo's own `signal_generation` and
`EG_method` on four bank and insurer pairs (2013 to 2014), first on raw prices and then on
prices multiplied by 10. A correct strategy makes identical trades both times.

| Pair | Entries, prices x1 | Entries, prices x10 |
|---|---|---|
| China Merchants Bank / Industrial Bank | 4 | 0 |
| ICBC / China Construction Bank | 19 | 17 |
| SPD Bank / Minsheng Bank | 4 | 2 |
| Ping An / China Pacific Insurance | 9 | 9 |

Under pandas 3 every row is 0.

**What survives honest execution.** Same signal logic, two ways of filling: "as repo" (same
close, no cost) and "honest" (next day's open, 0.1% per side). Equal weight across all names,
rebalanced daily. The MACD script asks the user for its two windows; I used 10 and 21. Dual
Thrust is rebuilt on daily bars with k = 0.5 and a 4-day range.

| Strategy | Annual return | Sharpe |
|---|---|---|
| Buy and hold (reference) | +12.3% | 0.41 |
| Heikin-Ashi, as repo | +2.9% | 0.36 |
| Heikin-Ashi, honest | +2.9% | 0.33 |
| MA cross 10/21, as repo | +9.6% | 0.58 |
| MA cross 10/21, honest | +8.2% | 0.46 |
| Dual Thrust, range includes today (as repo) | -50.7% | -12.15 |
| Dual Thrust, range ends yesterday (fixed) | -10.1% | -1.75 |

**Where the MA cross edge comes from.** Year by year, the honest MA cross lost 27% in 2008
against 81% for buy and hold, and that one year is most of its Sharpe advantage. Excluding the
two crash years (2008 and 2015), its Sharpe is 0.66 against 0.71 for simply holding. The trend
filter is a crash insurance policy that costs you in every normal year (2009: +47% vs +93%;
2019: +20% vs +36%).

**Sweeping the windows makes it worse, not better.** The MACD script asks the user for two
windows, which invites trying many and keeping the best. I swept 415 (fast, slow) pairs on
2008-2014 and looked at 2015-2021, honest execution throughout:

| | Sharpe 2008-2014 | Sharpe 2015-2021 |
|---|---|---|
| Best pair in-sample (42 / 100) | 0.82 | 0.37 |
| Top 10% of pairs in-sample (average) | 0.75 | 0.36 |
| Median pair | 0.56 | 0.39 |
| Buy and hold | 0.33 | 0.53 |

The chosen pair did worse out of sample than 61% of all the pairs, and the rank correlation
between in-sample and out-of-sample Sharpe across pairs was negative (-0.19). Picking the best
backtest selected for whatever happened to suit 2008-2014, mostly sitting out the 2008 crash.

**Look-ahead does not always flatter.** The Dual Thrust leak made results far worse here, not
better: putting today's range into today's bands places entries near the day's extremes. The
lesson is not "look-ahead inflates returns", it is "look-ahead makes the number meaningless
in an unknown direction". (Dual Thrust is a day trade, which A-share T+1 rules forbid for new
buys, so treat this as a test of the backtest logic, not a China strategy.)

## The edge, in one line

The scripts are good teaching material for how each indicator is computed. The only edge that
survived honest testing is the oldest one: a moving-average trend filter that sidesteps part of
a major crash, paid for with lower returns in ordinary years.

## Takeaways for our own work

- Fill on the next bar, always, and charge costs. Same-bar fills at zero cost should be
  treated as a bug.
- Any rolling statistic used for an intraday threshold must end on the previous session.
- Run a scale test (multiply prices by 10) on any stat-arb or options code. Unit bugs show up
  instantly. For options, keep premiums, strikes and spot in the same currency per contract.
- Pin library versions. Silent behaviour changes (pandas copy-on-write) can turn a strategy
  off without an error.
- Never ship the best cell of a parameter sweep. Pick from a stable region, then confirm on a
  later period.
- Judge trend filters on non-crash years separately. If the edge is one crash, size it like
  insurance, not like alpha.

## Reproduce

```
curl -L -o cn.zip https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_simple_cn_1d_latest.zip
unzip cn.zip -d cn
git clone --depth 1 https://github.com/je-suis-tm/quant-trading
python experiments/execution_and_lookahead.py ./cn
python experiments/ma_sweep_overfit.py ./cn
# pairs test runs the repo's own functions; needs pandas 2.x and statsmodels
pip install "pandas<3" statsmodels matplotlib
python experiments/pair_trading_scale_test.py ./quant-trading ./cn
pip install openpyxl
python experiments/options_straddle_check.py ./quant-trading
```
