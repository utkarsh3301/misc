# 05. Vibe-Trading (HKUDS personal trading agent)

Repo: https://github.com/HKUDS/Vibe-Trading
Studied: shallow clone of `main` (v0.1.15+), October 2026.

## What it is

An LLM agent that turns a plain-language request ("backtest a momentum strategy on these
stocks", "analyse my broker export") into data loading, strategy code, backtests and a report.
It ships market-specific backtest engines (China A, India, Korea, Vietnam, US and global
equities, futures, forex, crypto, options), an "Alpha Zoo" of published factor libraries (Alpha
101, GTJA 191, Qlib 158 and others), connectors to 18 brokers, and a "Shadow Account" that reads
your own trade history and diagnoses behavioural biases.

## How it works (from the source)

| Piece | Where | Detail |
|---|---|---|
| Agent loop | `agent/src/agent`, `agent/src/swarm` | The LLM plans, calls tools (loaders, backtest, factor bench), reads results, iterates. A "swarm" mode runs several worker agents as an investment committee. |
| Engines | `agent/backtest/engines/*.py` | One engine per market, each encoding that market's rules: lot sizes, settlement, price limits, taxes. |
| Factors | `agent/src/factors` | The Alpha Zoo, plus a bench that scores factors (IC, returns) on CSI300 or S&P 500 members. |
| Shadow Account | `agent/src/tools/trade_journal_tool.py`, `agent/src/shadow_account` | Parses broker CSVs, pairs trades FIFO, computes profile stats and four bias detectors, then extracts "your rules" and backtests them. |

## Where the edge is supposed to come from

Two places: (1) speed, letting one person test many ideas with correct market mechanics, and
(2) self-knowledge, finding the behavioural leaks in your own trading.

## What I found

### 1. The changelog is a ledger of backtest bugs worth reading on its own

This is one of the most actively maintained projects in the space, and its own release notes
record the kinds of bugs that quietly inflate or distort a backtest. A selection, all from 2026:

| Bug | Effect | Fixed |
|---|---|---|
| Every A-share basket loaded from six data sources was routed to the crypto engine | No stamp tax, no T+1, no price limits, no 100-share lots, plus an 8-hourly perpetual funding fee. "The run succeeded and its metrics were internally consistent, which is what made it dangerous." | Sep 14, #1431 |
| Carhart momentum factor subtracted the 1-month return from the 12-month one | The factor moved with today's close | Sep 30, #1578 |
| Announcement dates have no time of day | On intraday bars a filing was visible from the first bar of its own day: a full session of look-ahead | Sep, #1387 |
| Returns across a trading halt were recorded as 0 | Understated volatility, inflated Sharpe | Jul 29 |
| All five portfolio optimisers | Look-ahead bias | #487 |
| 24 Alpha Zoo factors | A missing bar inside the window made a comparison read False and emit a constant | Sep 21, #1523 |
| Alpha bench on CSI300 / S&P 500 | Survivorship bias, now disclosed in the report | #859, #1289 |

If a project with dozens of contributors and a large test suite shipped these, any home-grown
backtester should be assumed to have some of them too.

**Independent check: the Alpha Zoo is clean today.** I ran all 462 factors through the
project's own `Registry.compute()` on 40 CSI300 stocks (2016 to 2020) and applied the truncation
test from 08-ta-libraries: recompute each factor with every bar after a cut date deleted, at 6 cut
dates, and compare. 437 factors ran (23 were skipped by the registry for needing sector, market cap
or fundamentals; 2 raised errors), and none changed its value on day t when later bars were
removed. Whatever bugs the changelog records, the factor library as shipped passes.

### 2. The India engine (relevant to NSE work)

`agent/backtest/engines/india_equity.py` models NSE cash delivery on daily bars. The cost stack
matches the published rates as of 2026 (verify before relying on them): STT 0.1% on both sides, stamp duty 0.015% on buys, NSE
transaction charge 0.00297%, SEBI fee Rs 10 per crore, GST 18% on brokerage and charges. Gaps:

- **One circuit band for every stock, default 20%.** Many small and mid caps sit in 2%, 5% or
  10% bands, and those are exactly the names a reversal or breakout strategy wants. A 20% band
  lets the backtest fill trades that would have been locked in reality. (See 01-qlib: ignoring
  limits overstated a reversal strategy by about 6 points a year.)
- **"T+1" treated as a same-day sell ban.** It blocks selling shares bought on the same bar
  (the circuit check itself is imported from the China engine).
  India's T+1 is a settlement cycle, not a trading ban: a same-day sale is allowed and is simply
  taxed as intraday. Harmless on daily bars, wrong for anything finer.
- **DP charges default to 0.** The depository charge per scrip per sell day is small but
  matters for small accounts and frequent rebalancing.
- F&O lot sizes, margins and expiries are not modelled in this engine.

### 3. The Shadow Account bias detectors flag traders who have no biases

The four detectors are simple rules:

| Detector | Rule in the code | Severity medium / high at |
|---|---|---|
| Disposition effect | mean hold days of losing round trips / mean hold days of winners | 1.2 / 1.5 |
| Chasing momentum | share of buys priced more than 3% above the user's own buy 3 buys earlier in that symbol | 40% / 60% |
| Anchoring | share of symbols (with 5+ trades) whose trade prices have a coefficient of variation under 5% | 33% / 66% |
| Overtrading | PnL of round trips closed on busy days vs quiet days | gap of 30% / 100% |

I imported the real `_compute_behavior` function and fed it journals written by robots with no
emotions, one robot account per stock, on real CSI300 price paths:

| Robot | What it does | Disposition flagged | Chasing flagged | Anchoring flagged |
|---|---|---|---|---|
| SIP | buys 100 shares every 20 trading days for a year, sells once at the end | 28% | 51% | 6% |
| Coin flip | random entries, always sells exactly 10 trading days later | 0% | 37% | 0% |
| Bracket | random entries, +5% take-profit, -15% stop-loss | 97% | 64% | 0% |

- **Chasing is mostly measuring the stock's trend.** It compares each buy to the user's own
  earlier buys, not to the price path before the decision. A disciplined SIP into a rising stock
  gets labelled "strong chasing" half the time; a coin-flipper gets flagged over a third of the
  time.
- **Disposition by hold-time ratio cannot tell a rule from a bias.** The bracket robot decided
  its exits before entering, yet is flagged 97% of the time, because a wide stop and a tight
  target mechanically make losers last longer. The SIP robot is flagged 28% of the time purely
  from FIFO pairing in a falling market. The standard academic measure (Odean's proportion of
  gains realised vs proportion of losses realised, checked on every day the trader sells) is
  much harder to fool.
- Overtrading never fired for any robot, which says the check rarely has enough busy/quiet
  contrast in ordinary journals rather than that robots are virtuous.

## The edge, in one line

No market edge is claimed and none is built in. The real value is a fast research harness with
market rules encoded per country, and a changelog that doubles as a checklist of backtest
failure modes. The behavioural "Shadow Account" is a good idea with detectors that are too naive
to trust on their own.

## Takeaways for our own work

- Keep a written ledger of backtest bugs, like theirs. Each entry is a regression test.
- For Indian equities, load the actual per-scrip price band and F&O status daily instead of one
  global band.
- For behavioural diagnostics on our own trades, use PGR/PLR for disposition and compare buys
  with the price path before the decision for chasing. Run any detector on random and rule-based
  robots first to see its false-positive rate.

## Reproduce

```
curl -L -o cn.zip https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_simple_cn_1d_latest.zip
unzip cn.zip -d cn
git clone --depth 1 https://github.com/HKUDS/Vibe-Trading
python experiments/robot_traders_vs_bias_detectors.py ./Vibe-Trading ./cn
python experiments/alpha_zoo_truncation_test.py ./Vibe-Trading ./cn
```
