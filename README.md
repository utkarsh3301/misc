# Open-source trading tools: where is the edge?

Eight popular open-source trading tools, strategy collections and indicator libraries, read from the source code
and then tested on real market data. For each one the question is the same: where is the edge
supposed to come from, and does it survive an honest test?

All experiments use real daily data for China's CSI300 stocks (2005 to mid 2021, from qlib's
public dataset), with point-in-time index membership where it matters. Every number below can
be regenerated from the scripts in each folder.

## The short version

| # | Tool | What it claims | What the edge actually is | Biggest problem found |
|---|---|---|---|---|
| 01 | [qlib](01-qlib) (Microsoft) | Better ML models find more alpha | A short-term reversal and price-volume signal in A-shares, extracted with a regularised tree model | Fancy models add little (11 of 18 score below Linear). Edge shrinks after costs and price limits, and is decaying since 2017. A copy-paste error in the CSI500 benchmark table. |
| 02 | [TradingAgents](02-tradingagents) | An LLM "trading firm" with debating analysts | None demonstrated. Good research memos. | The paper predates a long list of data look-ahead fixes. The LLM itself knows the future on past dates. ~2,200 decisions needed to detect a 53% hit rate. |
| 03 | [FinRL](03-finrl) | Deep RL agents beat the index | Long-equity beta plus the luck of the test window | Random agents track buy-and-hold with 0.96 correlation; the best of 20 random agents beats it 80% of the time. The flagship test window is a bull run, and its VIX crash switch never fires there. |
| 04 | [quant-trading](04-quant-trading) (je-suis-tm) | Classic technical and stat-arb strategies | Only the oldest one: a moving-average filter that dodges part of a crash | Same-bar fills with no costs, a look-ahead in Dual Thrust, a unit bug that makes pairs trading depend on the price currency, an options straddle that undercounts its premium 10x. |
| 05 | [Vibe-Trading](05-vibe-trading) (HKUDS) | A personal trading agent plus bias diagnosis | Speed of research with per-market rules, no market edge | The bias detectors flag rule-following robots: a monthly SIP is "chasing" half the time. India engine uses one 20% circuit band for every stock. Its changelog is a great catalogue of backtest bugs. |
| 06 | [RD-Agent(Q)](06-rd-agent) (Microsoft) | An LLM mines factors for 2x the return | A cheap, fast factor-idea generator | Factors are accepted by looking at the test period. A noise proposer under the same rule "finds" IC that vanishes out of sample. |
| 07 | [FinGPT](07-fingpt) | Open financial LLMs for sentiment and forecasting | Cheap, accurate text classification | Forecaster targets are written by GPT-4 after being told the answer. Weekly stock direction is mostly the market's direction. |
| 08 | [ta and pandas-ta](08-ta-libraries) | Standard indicator libraries | Not strategies, but a leaking indicator manufactures a fake edge | An automatic truncation test: ta is clean (86 of 86). pandas-ta leaks future bars in DPO, Ichimoku, VHM, TOS StDevAll and zigzag by default; its zigzag "backtest mode" is one bar short; VHM passes a window length where Python expects a mean. |

## What they have in common

The same handful of mistakes shows up again and again. In rough order of how much damage they do:

1. **Choosing on the test set.** Picking the best model, strike, factor or agent after seeing
   the period you report on. (RD-Agent, FinRL comparisons, the options straddle. A 415-pair
   moving-average sweep picked a winner that then did worse than 61% of the pairs.)
2. **Testing on one friendly window.** A single bull run makes anything long look smart.
   (FinRL, FinGPT Forecaster.)
3. **Look-ahead in the data.** Today's high in today's threshold, future prices in position
   sizing, news without timestamps, an LLM that has read the future, indicators that peek.
   (quant-trading, TradingAgents before 2026, Vibe-Trading's own changelog, pandas-ta.)
4. **Fills that cannot happen.** Same-bar execution, no costs, ignoring price bands and
   locked limit moves. Ignoring limits alone overstated a reversal strategy by about 6 points
   a year. (quant-trading, qlib replica.)
5. **Unit and library bugs.** Adding a price to a z-score, counting a premium in the wrong
   units, a pandas upgrade that silently switches a strategy off. (quant-trading.)
6. **No baseline.** No random agent, no "always up", no "follow the index", no noise proposer.
   Every tool here looks better without one.

## Where real edge showed up

- **Short-horizon reversal in China A-shares** (qlib): real, measurable, monotonic across
  deciles. Thin after costs and limits, and fading.
- **Trend filter as crash insurance** (quant-trading MA cross): it cut 2008's loss from -81% to
  -27% but gave up return in almost every normal year. Its Sharpe advantage disappears once 2008
  and 2015 are excluded.

Neither is the kind of edge the tools advertise. Both come from market structure and from
risk control, not from the model.

## A checklist before trusting any backtest

- [ ] Signal at close t, fill at t+1 or later, with costs and taxes for that market
- [ ] Refuse fills at price bands and on halted days
- [ ] Point-in-time universe (no survivorship), point-in-time data (every field has a "known at" time)
- [ ] Every feature passes the truncation test (08-ta-libraries): its value on day t must not
      change when bars after t are deleted
- [ ] Selection done on validation, test window opened once
- [ ] Results across many windows, including crashes and sideways years
- [ ] Baselines run through the same engine: buy-and-hold, random, always-up, noise
- [ ] Scale test: multiply prices by 10, results must not change
- [ ] Count the trials; demand more from a winner chosen out of many
- [ ] For LLMs: only test on dates after the model's training cutoff

## If you trade NSE

Most findings carry over directly; a few get sharper:

- **Price bands.** Many NSE stocks outside F&O trade in 2%, 5%, 10% or 20% bands. A backtest that
  fills at the band is the same mistake that added about 6 points a year to the A-share reversal
  test in 01. Load each stock's band per day; one global band (05) is not enough.
- **Costs.** Delivery trades pay STT of 0.1% on both sides plus stamp duty, exchange and SEBI
  charges and GST, roughly 0.22% per round trip before slippage and DP charges. At qlib-style
  turnover (10% of the book a day) that is about 5.6% a year, close to the A-share cost drag.
  Verify current rates before relying on them; they change with budgets.
- **Settlement.** India's T+1 is a settlement cycle, not China's ban on selling same-day
  purchases. Engines borrowed from China models (05) get this wrong.
- **Algo rules.** Since April 2026 exchange-registered algo IDs, static IPs and a kill switch apply
  to API order flow, which matters for anything that goes from backtest to live.
- **F&O.** None of the eight tools models Indian lot sizes, expiries, margins or option STT
  properly. Any options backtest should pass the unit test in 04: premiums, strikes and spot all
  in rupees per lot.

## Reproducing

Every folder has an `experiments/` directory and a "Reproduce" section. The common data:

```
curl -L -o cn.zip https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_simple_cn_1d_latest.zip
unzip cn.zip -d cn
pip install numpy pandas lightgbm statsmodels matplotlib openpyxl ta pandas-ta
```

Scripts read qlib's binary files directly, so qlib does not need to be installed. Scripts that
import code from the studied repos take the path to a clone of that repo as an argument.
