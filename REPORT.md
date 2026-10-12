# Verifiable option-trading edges: what survives scrutiny

Branch `verify`. Working session on 2026-10-12. Every number below traces either to a file in `results/` (computed here from real data by the scripts in `scripts/`) or to a row in `ledger/claims.md` (reported by a source and not re-derived here). Row ids such as A11 or F19 refer to that ledger.

## 1. Bottom line

No strategy I examined meets the bar for a definite, verifiable edge: a positive expected profit after realistic costs, supported by statistics that survive fat tails and multiple testing, persisting out of sample, with a worst case an ordinary account can survive. The best-supported candidates are risk premia. They pay on average because they carry crash risk, which is different from a mispricing that can be harvested safely.

What the evidence supports, strongest first:

1. **Structural rules that are definite but are not trading alpha.** US broad-based index options (SPX, NDX, RUT) are Section 1256 contracts: gains and losses are taxed 60% long-term and 40% short-term whatever the holding period, and are marked to market at year end (D1). SPX options are European and cash settled, which removes assignment risk and is what makes box-spread financing workable (F22). These are rules, not statistics. They improve what you keep after tax. They do not create a pre-tax edge.
2. **An S&P 500 volatility risk premium exists on average.** Implied volatility has exceeded subsequent realized volatility by about 4.1 volatility points over roughly 35 years (F18), and by 3.0 points in the 2014 to 2018 data I tested, with the VIX above realized volatility in 82% of 21-day windows. The literature reads it as compensation for crash risk (A3, A14, H6) and finds it concentrated at short maturities (A2, F14); a June 2026 paper reports it has been structurally lower since about 2012 (H3). My tests found it statistically detectable in that sample, gross of costs, and also found five reasons it is not a definite edge (section 4): a selling concession of about 1.7 vol points erases the mean payoff of the variance proxy, one bad window erases about 19 months of average gains, the sample was among the calmest in the record, the track record is far too short to verify, and naive significance tests are inflated for this return shape.
3. **Single-stock option anomalies and event trades have the strongest gross statistics in the literature, but their status net of costs for a non-institutional trader is unresolved.** Examples are the realized-minus-implied volatility spread, idiosyncratic volatility, skewness, machine-learning characteristic sorts and pre-earnings straddles (B1 to B4, F8, F10, F12). Authors of several papers report profits after their cost assumptions (B2, B3, A11). Other work finds costs and margin erode most of it (F8, F11). I found no independent live replication and no measurement of post-publication decay for option anomalies (F17).
4. **Popular retail structures have negative evidence.** Retail 0DTE buying and cheap weekly out-of-the-money options show average losses in the evidence I found (C2, C3, F6, F7), and long out-of-the-money puts as protection show negative expected returns (A4, F4). "Free yield" covered-call products have only low-quality evidence behind them (C6). Regulator data from India put the share of individual derivatives traders who lost money at 91% to 93% (C5). A static-rule study of systematic 0DTE strategies found no consistent profitability (F5).

What I could not do is as important as what I did. The environment's egress policy blocked every market-data host I needed, so I ran no option-level backtest, no index-level test on actual PUT or BXM series, and no VIX-futures test. The literature was reached only through web-search summaries, so those numbers are second-hand. Section 8 lists exactly what to unlock to finish the job.

### Scorecard

Judgment against the six tests in section 2, using only the evidence cited in section 5. *yes* means supported, *mixed* means the evidence points both ways or covers only part of the question, *no* means evidence against, *untested* means I found no test, *n/a* means not applicable.

| Family | Mechanism | Statistics | Net of costs | Persistence | Survivable | Accessible |
|---|---|---|---|---|---|---|
| Index volatility selling | yes | mixed | mixed | mixed | mixed | yes |
| Short-dated (0DTE, weekly) selling | mixed | no | untested | untested | mixed | yes |
| Single-stock cross-section | mixed | yes | mixed | untested | mixed | no |
| Earnings straddles | mixed | mixed | mixed | mixed | yes | yes |
| Overnight and weekend effects | yes | mixed | no | untested | yes | no |
| Structural (tax, European, box) | yes | n/a | n/a | yes | yes | yes |

Notes on the cells that carry the argument. Index selling, statistics: detectable gross (HAC t 2.3 to 3.2 for the premium over five years; the PUT-versus-equities Sharpe difference has t 1.5 to 2.8 over three decades) but not robust to tail-aware inference. Index selling, net of costs: one net study (A11) against a 1.7 vol point break-even and a VIX-to-ATM gap of similar size (F19). Index selling, persistence: the lower-risk profile of PUT persists through 2023 but its return edge over equities has gone (A5b) and one paper reports a structural decline since about 2012 (H3). Short-dated selling, statistics: static hold-to-expiry rules show no consistent profitability (F5) and the premium at same-day horizons is modest (H4). Single-stock, statistics: Sharpe ratios above 2 gross in several papers (B2, B3). Single-stock, accessible: the signals are strongest in illiquid names with low analyst coverage (B3, F8).

## 2. The test applied

A claim counts as a verifiable edge only if it passes all six:

1. **Mechanism.** Who is on the other side and why do they pay?
2. **Statistics.** Enough independent observations, with inference that respects fat tails, autocorrelation and the number of variants tried.
3. **Costs and margin.** Net of realistic bid-ask, hedging, fees, financing and margin.
4. **Persistence.** Out of sample and after publication.
5. **Survivability.** The worst plausible loss, and the path to it, fit inside the account.
6. **Access.** A non-institutional trader can trade it at the assumed prices.

Labels used in the tables: *Verified here* (computed from real data in this repo), *Published gross*, *Published net* (net under the authors' own cost model), *Commentary only*, *Negative evidence*, *Rule* (structural).

## 3. What was possible in this environment

- **Blocked by the network policy:** cdn.cboe.com, www.cboe.com, fred.stlouisfed.org, stooq.com, query1.finance.yahoo.com, mba.tuck.dartmouth.edu, www.dolthub.com, www.alphavantage.co, export.arxiv.org, papers.ssrn.com, www.aqr.com, api.nasdaq.com. Package registries and raw GitHub content were reachable. A request to attach one public VIX-history repository to the session was denied and I did not route around it. The hosts were re-probed several times during the session and stayed blocked.
- **Real data used** (bundled in the Python `arch` package): S&P 500 daily OHLC 1999-01-04 to 2018-12-31; VIX daily closes 2014-01-03 to 2019-01-03; Fama-French monthly factors 1926-07 to 2018-11; Nasdaq composite daily (used only in tests). The VIX series has a low of 9.14 on 2017-11-03 and a high of 40.74 on 2015-08-24 (both agree with my recollection of the published closes, not checked against a source here), and the one-day jump on 2018-02-05 is 17.31 to 37.32 (+115.6%), against +117% in a published summary (`results/event_check.json`).
- **Not done:** no simulated or modelled option P&L is offered as evidence. One analysis is hypothetical and labelled as such (the power analysis in section 4.5).
- **Checks on the code:** 47 unit tests (`tests/`) including proofs that forward and trailing windows use only the intended returns and that no rule weight changes when future data is removed, a hand-computed fixture for the put-writing harness, and an independent recomputation of the headline premium numbers with explicit loops and a hand-written Newey-West estimator (no pandas rolling windows, no statsmodels) that matches the primary pipeline. A further test regenerates every number quoted in sections 3 and 4 from `results/` and fails if this text disagrees; when first run it caught four transcription errors in this report (an S&P 500 move quoted as a log return, two rounded percentages and a mean VIX quoted from a different window), all now fixed. Two code mistakes were also found and fixed along the way: a test with the wrong expected value (the code matched the published formula) and an off-by-one that dropped the first out-of-sample month in the rule test (section 4.6 uses the corrected numbers).
- **Data audit** (`results/data_audit.json`, G7): no duplicate dates; the daily change in log VIX has correlation -0.82 with the same-day S&P 500 return and about zero at lags of one or two days, so the two series are aligned; the Fama-French market return correlates 0.987 with the S&P 500 monthly price return over 238 months, so the factor dates parse correctly.
- **Provenance of literature numbers:** the full text of papers could not be opened. Where a number could not be recovered I left it out (for example the exact monthly return in Goyal and Saretto 2009, and the sample period of Zhan, Han, Cao and Tong 2022). See ledger row F24.

## 4. Real-data results (2014 to 2018 VIX, 1999 to 2018 S&P 500)

The test object is the short side of a 30-day variance swap proxy struck at VIX squared, plus a volatility-swap proxy struck at the VIX. Payoffs are per unit of strike, so a premium of 1.0 is collected and realized variance is paid out. All results are gross of costs and of margin. The sample has 1,236 daily 21-trading-day windows (59 non-overlapping).

### 4.1 The premium is there

![VIX versus delivered volatility](results/figures/fig1_vix_vs_realized.png)

- Mean VIX 14.7 against mean realized volatility 11.7: a gap of 3.0 vol points. The VIX was above realized volatility in 81.7% of windows (80.9% to 81.7% for 20 to 22 day windows). Realized variance averaged 73% of the strike variance.
- Short variance proxy: mean payoff +0.236 of the strike per window. Annualized Sharpe 0.94 averaged over the 21 possible monthly window grids (range 0.61 to 1.24). Volatility proxy: Sharpe 1.95 (range 1.67 to 2.16).
- Gross significance: HAC t = 2.6 for the variance proxy (2.3 to 3.2 across 10 to 63 lags) and 5.4 for the volatility proxy (4.7 to 6.6). A bootstrap null that resamples the observed tails gives one-sided p = 0.007 for the variance proxy (worst start grid 0.054) and no bootstrap draw reached the observed mean for the volatility proxy (p below 0.0003 on every grid).
- By calendar year, mean variance payoff per window: 2014 +0.31, 2015 -0.01, 2016 +0.45, 2017 +0.60, 2018 -0.20. In two of five years the average was flat or negative.
- The VIX squared over-predicts realized variance: the slope of realized variance on VIX squared is 0.49 (t = -6.5 against 1), R-squared 0.18. Trailing realized variance adds nothing. Using the ex-ante premium to forecast the next 21-day S&P 500 return gives R-squared 1.6% (t = 1.78); the 2007 working paper of Bollerslev, Tauchen and Zhou reports far more at the quarterly horizon with high-frequency realized variance (F23), so this is not a contradiction, only a reminder that five years of daily data are a weak instrument.
- Descriptively, the gap is larger when the VIX is high: 2.4 vol points when the VIX started at 9.1 to 12.5, 2.6 at 12.5 to 15.2 and 4.1 at 15.2 to 40.7. The worst windows came from selling at low VIX levels (worst payoff -5.3, against -3.3 in the top tercile). This is a description of 1,236 overlapping windows, not a validated rule (section 4.6).
- A range-based realized-variance estimator shows an even larger gap (4.5 vol points, t = 7.1) but averages only 83% of the close-to-close variance, so I kept close-to-close because it matches the contract definition.

### 4.2 Small gains, lumpy losses

![Monthly payoffs and a compounded 10% volatility-target curve](results/figures/fig2_monthly_payoffs.png)

- 81% of windows gain. Skew is -3.4 and kurtosis 16.4. The three worst non-overlapping windows start 5 Aug 2015 (payoff -4.44; VIX 12.5, delivered 29.2, S&P 500 -7.1%), 4 Jan 2018 (-3.03) and 4 Oct 2018 (-1.79). Across all 21 start grids the worst window starts 10 Aug 2015 at -5.35 (-5.25 if the swap is capped at 2.5 times strike volatility).
- The worst window erases 19.2 months of average gains for the variance proxy and 6.4 for the volatility proxy.
- Scaled to 10% annualized volatility and compounded, the variance proxy has a worst month of -14.0%, a maximum drawdown of -14.0% and a CAGR of 8.5% (final value $1.50 over 4.9 years). At a 30% volatility target the worst month is -41.9%. These ignore margin calls and costs.
- The payoff is short gamma: beta +21 per unit of 21-day S&P 500 log return (t = 3.7) and a squared-return coefficient of -330 (t = -3.5), R-squared 0.45 rising to 0.62. A linear CAPM alpha is not significant (t = 0.8 on the monthly grid) and is the wrong benchmark for a nonlinear payoff, which is the Broadie, Chernov and Johannes (2009) point (A3).

### 4.3 Costs, and the VIX is not the price of an ATM option

![Significance versus selling concession](results/figures/fig3_cost_sensitivity.png)

- Selling at the VIX minus c vol points: the variance proxy's mean payoff falls from +0.236 at c = 0 to +0.109 at c = 1.0 and -0.053 at c = 2.0. The break-even concession is 1.70 vol points and the HAC t falls below 1.96 after 0.4. For the volatility proxy the break-even is 2.76 and significance goes after 1.8.
- c is a stylized stand-in. I could not find a sourced SPX bid-ask in vol points (F24). One vendor article gives a rule of thumb that the VIX is about 1.1 to 1.2 times 30-day at-the-money implied volatility (F19), which is about 1.3 to 2.5 vol points at the sample's mean VIX of 14.7 (1.0 to 2.8 across VIX 11 to 17). A seller of at-the-money options therefore does not collect the VIX-based premium. Whether the lower tail sensitivity of a straddle offsets that gap cannot be tested without option prices.
- Constantinides, Czerwonko, Jackwerth and Perrakis report a net-of-cost utility gain from writing rich S&P 500 futures options out of sample over 1983 to 2006 (A11). That is their finding on a different sample and instrument, not something reproduced here.

### 4.4 The sample was calm

![Realized volatility 1999-2018](results/figures/fig6_realized_vol_context.png)

- Mean 21-day realized volatility was 11.7 in 2014 to 2018 against 16.3 over 1999 to 2018. That block ranks 2nd calmest of 16 rolling five-year blocks (2013 to 2017 is calmer at 11.0).
- Realized volatility at or above 40 occurred in 2.8% of all windows and in none of the 2014 to 2018 windows. The episodes are 2002 (peak 46), September 2002 (41), 2008 (84), 2009 (50) and 2011 (48). The worst 21-day log return was -35.7% against -12.0% inside the window.
- Break-even strike (`results/tail_frequency.json`): the strike at which a short-variance seller breaks even is the square root of mean realized variance. Over 1999 to 2018 it is 19.1 vol points against a mean realized volatility of 16.3; excluding 2008 and 2009 it is 16.4, and in 2014 to 2018 it was 13.0 against an average strike of 15.3 in variance terms (mean VIX 14.7). The crisis windows are what the seller must be paid for, and selling at calm-regime VIX levels is a bet that none arrives during the holding period. This compares realized variance across regimes and is not a statement about what the VIX was before 2014.
- A June 2026 paper reports a structural break in the S&P 500 variance risk premium around 2012 (H3; read only through a search summary). If so, the whole 2014 to 2018 window sits in the lower-premium regime, which would also help explain a gap of 3.0 points against the 4.1 long-run average.
- The sample also ends before March 2020 and April 2025 (the VIX closed at 52.33 on 8 April 2025, its highest close since 2020, per one source; H2), so those stress tests are not in it either.
- Arithmetic, not data: per unit of strike variance a short variance position pays 1 minus (RV/VIX) squared. At a VIX of 15 that is -6.1 at realized volatility 40, -15.0 at 60 and -27.4 at 80 if uncapped. A capped swap limits the loss to -5.25. Defined-risk option structures cap the loss differently.
- So +0.236 per window and a Sharpe near 0.9 describe a calm sample, not a full cycle. The long-run gap of 4.1 points (F18) sits on a higher level of realized volatility (15.5), so this sample is not simply a smaller copy of the full-cycle record.

### 4.5 A record this short cannot verify it

![Rolling-window verification rates](results/figures/fig4_rolling_verifiability.png)

- Sharpe 0.87 with a Mertens standard error of 0.66 and a bootstrap 95% interval of 0.02 to 2.88. With the observed skew and kurtosis, 7.5 years of data are needed just to reach one-sided 95% at the point estimate (3.7 if returns were normal). The sample has 4.9 years.
- Dropping the single worst window lifts the Sharpe from 0.87 to 1.58, and dropping January and February 2018 start dates gives 1.18.
- Windows overlap, so the shares below describe this one 92-year history and are not independent trials. Even for the equity premium, with a full-sample Sharpe of 0.43, only 28% of rolling 5-year windows have t above 1.96 (17% have a negative mean), 31% of 10-year, 55% of 20-year and 80% of 30-year windows. Value: 18%, 32%, 70%, 85%. Size: 14% at 5 years and 19% at 30 years.

![Power and false positives](results/figures/fig5_power_curves.png)

- Hypothetical power analysis (not a performance claim). If the true Sharpe is 0.5, five years of data show t above 1.645 only 30% of the time under normal returns. Years needed for 80% power: 25 (normal) and 39 (short-volatility shape) at a true Sharpe of 0.5; 6.5 and 14 at a true Sharpe of 1.0.
- With the short-volatility return shape, a strategy with zero edge passes the one-sided 5% test 16%, 12% and 9% of the time at 3, 5 and 10 years. The shape comes from only 59 months, so real tails are probably heavier and the distortion larger. A likely reason the curves are not monotone at short horizons is that short samples often contain no large loss.

### 4.6 Conditioning rules do not rescue it

Six rules fixed before looking at results, with a split at 2016-12 (2015-01 to 2018-11, 47 monthly windows). Details in `results/conditional_rules.json`.

| Rule | Share invested | Sharpe, offset 0 | Sharpe, avg of 21 grids | Grid range | In-sample | Out-of-sample | Worst month |
|---|---|---|---|---|---|---|---|
| R0 always sell | 100% | 0.78 | 0.80 | 0.49 to 1.17 | 0.62 | 0.95 | -4.04 |
| R1 VIX above its 1-year median | 49% | 1.46 | 0.83 | -0.12 to 2.35 | 2.18 | 0.86 | -1.14 |
| R2 ex-ante premium positive | 81% | 0.49 | 0.67 | 0.45 to 0.97 | 0.09 | 0.93 | -4.04 |
| R3 VIX below 20 | 91% | 0.70 | 0.64 | 0.31 to 1.00 | 0.47 | 0.95 | -4.04 |
| R4 volatility-managed (cap 2x) | 100% | 0.57 | 0.86 | 0.44 to 1.43 | 0.54 | 0.60 | -6.43 |
| R5 skip after a loss below -1 | 94% | 0.77 | 0.75 | 0.42 to 1.19 | 0.55 | 1.00 | -4.04 |

- The best in-sample rule (R1, in-sample Sharpe 2.18) earned 0.86 out of sample against 0.95 for always selling. The rule that happened to do best out of sample (R5, 1.00) differs from always selling by 0.05, which is noise. R1's Sharpe ranges from -0.12 to 2.35 depending only on which trading day the monthly grid starts on, so a 47-month sample cannot rank rules.
- The volatility-managed rule, which leverages up when recent volatility is low, took the worst month (-6.43), consistent with the out-of-sample weakness reported for volatility-managed strategies (F16).
- Deflated Sharpe ratios across the six trials are 0.78 to 0.90 for every rule including the baseline. With six highly correlated trials the deflation is mild, and the statistic says each Sharpe beats a luck level. It does not say any rule improves on always selling.

### 4.7 Mechanism check: weekends carry about one day of variance

- Friday close to Monday close variance is 1.25 times an ordinary day over 1999 to 2018 (1.01 excluding 2008 and 2009, 0.97 in 1999 to 2007, 1.08 in 2010 to 2018), against 3.0 on a calendar-time clock. Mean absolute returns give 0.96 to 1.02.
- This supports the premise of the weekend and night option-mispricing papers (B5, B6): if theta is charged on a calendar clock, weekends are over-charged by roughly a factor of three. It is not a profit test. An earlier working paper by Jones and Shemesh found little weekend effect for S&P 500 index options, and the gross effects elsewhere are mid-quote results that costs swamp for most traders (B5, B6). The index open is stale in several early years (open equals prior close on roughly 95% or more of days in 1999 to 2005), so the overnight split is limited to 2007 to 2018 and I rely on close-to-close results.

### 4.8 Arithmetic on published index statistics

`scripts/run_published_stats_arithmetic.py` uses summary figures from the ledger, not data from this repo, and an assumed risk-free rate.

- PUT versus the S&P 500 total return index, June 1986 to December 2015: Sharpe 0.67 against 0.47 (A5). The difference is 0.20; the test for equal Sharpe ratios gives t = 1.5, 1.7, 2.05 and 2.8 for assumed correlations of 0.80, 0.85, 0.90 and 0.95. The sources do not give the correlation.
- Cboe figures to August 2023: PUT 9.40% a year against 9.91% for the S&P 500, volatility 10.26% against 15.38%, maximum drawdown -32.7% against -51.0% (A5b). With a 3.4% risk-free rate the Sharpe ratios are 0.58 and 0.42 and t ranges from 1.4 to 2.7 across the same correlations. The return advantage over equities visible through 2008 (10.32% against 8.77%) has become a shortfall; the volatility and drawdown advantage remains.
- Implied linear CAPM alpha with beta 0.55 (F1): 2.4% to 3.3% a year, iid t of 2.4 to 3.3 across risk-free rates of 4.5% to 2.5%. Mixed windows, gross, and the wrong benchmark for a short-gamma payoff. A fund that tracks it launched with a 0.38% expense ratio (F2).
- Sponsor and third-party context: Cboe reports that PUT, BXM and two related indexes had higher Sharpe and Sortino ratios than equities over 32.5 years and itself notes that the Sharpe ratio assumes normality while these indexes are negatively skewed (I4); a Callan sample for 1988 to 2006 put the BXM Sharpe at about 0.52 against 0.30 for the S&P 500 (I4).
- Reading: after 30 to 37 years the index-level evidence for a risk-adjusted advantage is borderline to moderate, before costs, and highly model dependent.

## 5. Verdicts by strategy family

Why the premium exists, per the mechanism literature: end users are net long index options, especially out-of-the-money puts, and intermediaries who cannot hedge perfectly charge for inventory and unhedgeable risk (G1, G3); illiquid options earn compensation for liquidity provision (G4); and hedge-fund strategies that look like alpha often turn out to carry short-put exposure with left-tail risk (G5). All three put an institution with better execution on the other side of a retail trade (C1), which is why costs decide the retail outcome.

| Family | Edge claim | Best evidence | Net of costs | Status and verdict |
|---|---|---|---|---|
| Index put-writing, buy-write, covered calls | Earns equity plus volatility premia with lower volatility | A1, A5, A5b, A6 to A10, A11, F1, F2, H3; section 4 | One study net (1983 to 2006); index results gross | **Risk premium, positive on average, not a definite edge.** Verified here as a premium that is real but fragile and not verifiable in 5 years |
| Defined-risk index structures (iron condor, iron butterfly, collars) | Lower volatility and drawdown than equities | I1, I2, I3 | Gross | **Sponsor-produced index evidence only;** Sharpe figures for the condor and butterfly indexes were not retrieved and no net-of-cost test was found |
| Volatility-conditioned selling (sell more when the VIX or IV rank is high) | Premium scales with the level of implied volatility | A8, F20, F16; sections 4.1 and 4.6 | Gross | **Plausible, unverified.** The slope of realized on implied variance is 0.49 and the vol-point gap was 4.1 in the top VIX tercile against 2.4 in the bottom, and published work finds higher hedged Sortino ratios when the VIX is above 21 (F20); but the one rule I tested (R1) could not be separated from always selling in 47 months, and volatility-targeted rules tend to fail out of sample (F16) |
| Short variance, VIX-futures carry | Roll yield and variance premium | A12, A13, F20, F21; section 4 | Gross | **Premium documented, structure risk is real** (XIV terminated 2018). Not tested net here |
| Weekly and 0DTE selling | Largest premium at the shortest horizon | C4, F5, F6, H4, H5 | Mostly hold-to-expiry, gross | **No verified edge.** A static-rule study found none and the same-day premium is modest (H4); retail naked sellers were profitable on average but are about 13% of trades (H5); positive claims otherwise come from vendors or selected samples |
| Weekly and 0DTE buying (retail) | None | C2, C3, C5, F6, F7 | Yes | **Negative evidence** |
| Long OTM puts, tail hedging | Protection | A4, F4, F10 | Gross | **Negative expected return;** insurance with a cost budget, not an edge |
| Skew, correlation, dispersion, calendar spreads | Skew and correlation premia | A14, A15, F3, F14 | Mostly not exploitable after frictions | **Premia documented, not harvestable by retail.** Dispersion profits disappeared after 2000 |
| Single-stock cross-section (vol spread, IVOL, skewness, ML sorts) | Strong long-short returns | B1, B2, B3, F8, F9, F10, F11 | Conflicting | **Strongest gross statistics; net and capacity unresolved;** no independent live replication; hardest in illiquid names |
| Earnings straddles | 3.34% over three pre-earnings days (1996 to 2010) | B4, F12 | Partly | **Unresolved after 2010;** only commentary-grade evidence, partly pointing the other way |
| Overnight and weekend effects | Options mispriced over closures | B5, B6; section 4.7 | No; frictions swamp | **Mechanism confirmed,** profit accrues to market makers |
| FOMC and macro-day volatility | Premium highest on event days | F13 | No | **Unverified** |
| Structural: Section 1256, European cash settled, box spreads | Rules | D1, F22 | n/a | **Definite, not alpha** |
| Put-call parity and borrow-cost arbitrage (conversions, reversals) | Prices violate parity in the direction short-sale costs predict | J1 | Persists after options and lending costs per the authors | **Closest to a definite edge in the literature, but conditional:** it needs the ability to short and borrow stock, the largest gaps sit in costly-to-short stocks, and the evidence is a 2004 paper; I found no sign a retail trader can capture it |
| Early exercise and dividend capture | Free money from exercising deep in-the-money calls | J3 | n/a | **No retail free lunch found:** early exercise is rational mainly for institutions facing short-sale, transaction or funding frictions |
| Dealer-gamma timing and intraday momentum | Option-dealer hedging moves prices late in the session | J2, C4 | n/a | **Mixed and unverified as an option edge:** intraday momentum linked to gamma hedging is documented in futures (J2) while 0DTE gamma was found not to amplify returns (C4) |
| Mechanical management (50% profit target, exit at 21 days) | Higher return or lower drawdown than holding to expiry | G6 | Often unstated | **Unverified:** vendor in-sample backtests only, no Sharpe ratios, no independent study |
| Covered-call ETFs | High income | C6, H1 | n/a | **Unverifiable here;** equity beta plus short volatility |
| Crypto option selling | Large premium | F15 | n/a | **Unverified;** short samples, extreme tails |
| Retail derivatives outcomes | n/a | C5, C2, F7 | Yes | **Most lose** (91% to 93% in India; losses in the US and Netherlands) |

## 6. Verification protocol for any option-strategy claim

1. **Data.** Point-in-time bid and ask, not mid. Settlement conventions, dividends, corporate actions, no survivorship.
2. **Fills.** Sell at the bid and buy at the ask plus slippage. Do not assume effective spreads inside the quote unless you can trade that way (C1, F11).
3. **Margin and financing.** Ignoring margin dramatically overstates short-option returns (F11).
4. **Independent observations.** Count non-overlapping trades. Report results for every start grid, as in section 4.6, because the Sharpe moves a great deal with the grid.
5. **Tail-aware inference.** Performance measures such as the Sharpe ratio and alpha can be gamed and misstate payoffs with option-like tails (E2), so use a skew and kurtosis adjusted Sharpe standard error, block bootstrap intervals and years-needed estimates. Add a stress block with the known episodes (2008, August 2015, February 2018, March 2020, April 2025).
6. **Multiple testing.** Log every variant tried and deflate the Sharpe ratio for the number of trials (E1). Compare each rule with its baseline, not with zero. Demand t above 3 for newly mined effects (Harvey, Liu and Zhu, G2).
7. **Out of sample.** Pre-register rules, split by time, test other markets and the period after publication; for stock anomalies returns are 26% lower out of sample and 58% lower after publication (E3).
8. **Benchmark.** Option payoffs are nonlinear. Report downside beta and a squared-market term, not only a CAPM alpha.
9. **Capacity.** State the size at which spread and impact double.
10. **Kill criteria.** Write the loss and the shortfall in net Sharpe that end the strategy before starting.
11. **Tax and margin regime.** Section 1256 status, assignment risk, and the broker's margin treatment.

## 7. Pre-registered designs for the three best candidates

Each design fixes the rule, the fills and the pass and kill criteria before any data are looked at, so that a result is a test and not a search. Thresholds are conventions chosen for conservatism, not laws; the t-statistic of 3 follows Harvey, Liu and Zhu (G2) and the rest are my choices.

| | A. Index volatility selling | B. Single-stock cross-section | C. Earnings straddles |
|---|---|---|---|
| Fixed rule | Sell one 30 to 45 day SPX put at about 16 delta, cash secured with T-bills, hold to expiry; a second variant uses a put spread for defined risk. Size so a 20% one-month market fall loses no more than a stated share of equity | Monthly delta-hedged at-the-money straddle, long the top and short the bottom decile of the realized-minus-implied volatility spread (B1), liquidity filters fixed in advance | Buy the at-the-money straddle three days before the announcement when the mean absolute move over the last 8 quarters exceeds the implied move by a fixed ratio; hold to the announcement |
| Data | SPX chains with bid and ask, 15 or more years including 2008, 2011, 2015, 2018, 2020 and 2025; VIX; T-bill rates | Stock option chains with bid and ask for 20 or more years, stock prices, dividends | Earnings dates and option bid and ask around each event; 2010 onward kept separate |
| Fills and costs | Sell at the bid, buy back at the ask, plus commissions and fees; no effective-spread credit | Report quote fills, half the quoted half-spread and mid; charge margin and financing on short legs | Quote fills; skip contracts whose spread exceeds a fixed share of the price |
| Primary statistic | Net monthly excess return on non-overlapping months for every start grid; downside beta and squared-market control; block bootstrap; years needed | Net long-short return; Newey-West and bootstrap t; deflated Sharpe over every variant tried | Net return per trade; trade count; t-statistic; split before and after 2010 |
| Pass | Premium verified: net mean above zero with bootstrap p below 0.01 over 15 or more years covering three or more stress episodes. Edge verified: also alpha t of at least 3 after the controls and a positive net alpha in the second half | Net t of at least 3 at half-spread fills, positive in both halves and after 2010, and net of margin cost | Net t of at least 3 on at least 1,000 post-2010 trades, positive in at least 4 of the last 5 years, and an explicit comparison with the 1996 to 2010 result (B4) |
| Kill | Any month loses more than the stated budget, or realized cost per trade eats more than a fixed share of the gross premium | Post-2010 net return is not positive at half-spread fills | Net average per trade is negative over 12 months or 200 trades |

Design A has a ready harness, `src/putwrite.py` with `scripts/run_putwrite_backtest.py`: it fixes the rule (target days to expiry, target delta, bid or mid fill, fees, cash-secured collateral with interest, no overlapping positions) and reports the same statistics as section 4. It is unit-tested against a fixture whose answers were computed by hand (calendar arithmetic, selection, fills, payoffs, no-look-ahead, skipping rules) and has never touched market data. Its vendor column layout for one data format is recalled, not checked.

A failure at quote fills falsifies the edge for a retail cost model, not for a market maker. A pass at mid fills and a failure at quote fills is the typical shape of the cost-sensitive results in F8 and F11.

## 8. What to unlock to finish the verification

| Needed | Why | Would resolve |
|---|---|---|
| Allow cdn.cboe.com | Cboe publishes daily history for its strategy benchmark indexes (for example PUT, BXM, WPUT, CLL, CNDR), VIX, SKEW and VIX futures settlements (recalled, not verified in this session) | Index-level tests over 2008, 2020 and 2025 with `scripts/run_index_compare.py`; extend the premium study from 5 years of VIX to roughly 25 or more |
| Allow fred.stlouisfed.org and mba.tuck.dartmouth.edu | Risk-free rates and daily factors | Replace the assumed risk-free rate; alpha regressions |
| Paid or sampled option chains | Free SPX or SPY end-of-day chains were not found; one vendor lists SPX history by month and another end-of-day chains from 2010 (D2) | Actual bid-ask in vol points, ATM versus VIX gap, Design A with fills at bid and ask via `scripts/run_putwrite_backtest.py` |
| Paper access (ssrn, arxiv, journals) | Primary text | Replace second-hand numbers, recover the missing figures in F24 |

`src/index_compare.py` and `scripts/run_index_compare.py` are written and unit-tested on bundled equity series only. They have never been run on an option-strategy index.

## 9. Limitations

- Literature numbers are second-hand and some secondary sources conflict. Rows with weak sources are marked in the ledger.
- The real-data premium test uses a 5-year sample and a variance-swap proxy. The VIX includes skew and is not the price of an at-the-money option (F19).
- Windows overlap; inference uses HAC errors and non-overlapping grids, and the short-volatility return shape in the power analysis comes from 59 observations.
- Costs enter only as a stylized selling concession. No margin dynamics.
- The `arch` package does not document the vendor of its bundled VIX and S&P 500 series. Their extremes and event dates agree with my recollection of published figures, but I could not check them against Cboe.
- This is research, not investment advice. Short option positions can lose many times the premium collected.

## 10. Reproduce

```
pip install -r requirements.txt
bash run_all.sh
```

`run_all.sh` runs every analysis script, then the figure builder, then the unit tests (one compares an independent recomputation with the results files and another checks that the numbers quoted in this report match them). Outputs land in `results/`, figures in `results/figures/` with a CSV copy of each figure's data in `results/figures/data/`.

## Appendix: every variant run in this study

This is the "log every variant tried" rule applied to the study itself. The base case (21 trading day window, strike at VIX squared, close-to-close realized variance, Newey-West with 20 lags) was fixed before any result was seen. Everything else is a sensitivity reported as a range. No variant was dropped.

| Dimension | Variants run | Where reported |
|---|---|---|
| Payoff definition | 3: short variance, short variance capped at 6.25 times strike, short volatility | 4.1 to 4.3 |
| Window length | 3: 20, 21 and 22 trading days | 4.1 |
| Monthly grid start | 21 offsets, shown as ranges | 4.1, 4.5, 4.6 |
| HAC lags | 5: 10, 20, 30, 42, 63 | 4.1 |
| Realized variance estimator | 2: close-to-close (base) and range-based plus overnight gap | 4.1 |
| Selling concession | 31 levels from 0 to 3 vol points | 4.3 |
| Conditioning rules | 6, none tuned; deflated Sharpe uses 6 trials | 4.6 |
| Descriptive splits | VIX terciles (3), calendar years (5), four weekend sub-samples | 4.1, 4.7 |
| Power analysis grid | 6 true Sharpe values (including 0) by 11 horizons by 2 return shapes | 4.5 |

## File map

- `ledger/claims.md`: source-tracked claims with status codes.
- `src/`: `vrp.py` (windows and payoffs), `stats_utils.py` (Sharpe inference, deflated Sharpe, bootstraps, power), `index_compare.py` (strategy versus benchmark battery).
- `scripts/`: one script per analysis, `make_figures.py`, `run_index_compare.py`.
- `tests/`: unit tests including look-ahead checks.
- `results/`: JSON and CSV outputs of every analysis.
