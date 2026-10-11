# 02. TradingAgents (multi-agent LLM trading firm)

Repo: https://github.com/TauricResearch/TradingAgents
Paper: arXiv 2412.20138
Studied: shallow clone of `main` (v0.5.x), October 2026.

## What it is

TradingAgents simulates a trading firm made of LLM roles. Analysts read data, a bull and a bear
researcher argue, a research manager decides, a trader proposes a trade, three risk analysts
argue again, and a portfolio manager issues the final call for one ticker on one date.

## How it works (from the source)

The pipeline is a LangGraph state machine built in `tradingagents/graph/setup.py`:

```
Market, Sentiment, News, Fundamentals analysts   (run in parallel, each with tool calls)
        |
Bull researcher <-> Bear researcher              (max_debate_rounds, default 1 each)
        |
Research Manager  ->  Trader
        |
Aggressive -> Conservative -> Neutral risk analysts   (max_risk_discuss_rounds, default 1)
        |
Portfolio Manager  ->  one of: Buy / Overweight / Hold / Underweight / Sell
```

| Piece | File | Detail |
|---|---|---|
| Models | `default_config.py` | Two tiers: a "quick" model for analysts, debaters and trader, a "deep" model for the two managers. |
| Output | `agents/rating.py` | A regex reads the 5-tier rating out of the manager's free text. If it cannot find exactly one consistent rating, it returns `REVIEW` instead of guessing Hold. |
| Prompt steering | `managers/portfolio_manager.py` | The final prompt says "conflict alone is not a reason to Hold. Commit to the stronger case". The authors had to push the model away from always answering Hold. |
| Memory | `memory/settlement.py` | After 5 trading days each past decision is scored against its realised return and alpha, an LLM writes a one-paragraph "lesson", and the next run reads recent lessons. |
| Social screening | `agents/post_screen.py` | Optional: StockTwits and Reddit posts are screened by TypeSafe's Jev model, which returns calibrated probabilities for "is this post about the stock" and "which way does it lean". |
| Scoring | `backtest.py` (`summarize`) | Hit rate and mean alpha per rating bucket over a ticker and date grid. |

## LLM calls per decision

Counting from the graph: 4 analysts with up to 20 tool rounds each (typically 2 to 5 calls),
2 researcher turns, 1 research manager, 1 trader, 3 risk turns, 1 portfolio manager, plus 1
reflection per settled past decision. Roughly 20 to 30 LLM calls, several of them on the
expensive tier, for one ticker on one day.

## Where the edge is supposed to come from

Structured debate is supposed to reduce single-model bias, and the role split is supposed to
mimic how a real desk combines fundamental, sentiment, news and technical views.

## What I found

**1. The data look-ahead was only fixed in 2026, after the paper.** The changelog and code
comments document a long list of leaks closed between v0.3.1 (July 2026) and v0.5.2 (September
2026): Yahoo news articles without a parsed date bypassed the date filter and "leak future news"
(issues #992, #1007), today's StockTwits and Reddit chatter flowed into historical runs (#1220),
FRED macro data leaked post-decision values (#1275), company-overview and fundamentals
endpoints served today's figures into past dates (#1300), and the memory log could feed lessons
resolved after the trade date into that date's decision (#1251).
The paper (December 2024) predates all of these fixes, so its backtest numbers were produced on
a pipeline that could see the future through several doors.

**2. One leak cannot be fixed in code: the model itself.** Running a 2023 date through a model
trained on 2024 text means the "analysts" may already know what happened next. The repo has no
guard for this (I searched for any knowledge-cutoff check and found none). The only clean test
is on dates after the model's training cutoff.

**3. The live inputs still drift.** The README says it plainly: news, StockTwits and Reddit
"return different content as time passes", so a historical date run today sees different
inputs than the same date run last week. The backtest is not repeatable.

**4. The scorer cannot detect an edge at realistic sample sizes.** `summarize` reports hit rate
and mean alpha per rating, with no costs and no confidence interval. To tell a 53% hit rate from
a coin flip (95% confidence, 80% power) you need about 2,200 independent decisions. At 20 to 30
LLM calls each, that is 44,000 to 66,000 calls, and decisions on the same date across
tickers are not independent (they share the market move), so the real requirement is higher.

**5. The technical indicators themselves are clean.** The market analyst computes its
indicators with stockstats. I ran all 13 it requests through a truncation test (see
08-ta-libraries): none use future bars.

**6. The output is a mood, not a position.** Buy / Overweight / Hold / Underweight / Sell has no
size, no stop, no horizon other than the 5-day scoring window. Turning it into a portfolio is
left to the user.

## The edge, in one line

No demonstrated trading edge. What it does well is produce a readable, multi-angle research
memo for one stock, and the 2026 releases are a careful catalogue of every way an LLM backtest
can cheat. That catalogue is the most valuable part.

## Takeaways for our own work

- Treat an LLM trading backtest on dates before the model's training cutoff as contaminated.
- Every data source needs a "published at" timestamp and a filter, including news, social,
  macro and the agent's own memory.
- Budget the sample size first: work out how many decisions you need to see a 52 to 55% hit rate,
  then price the LLM calls. That number usually ends the project or reshapes it.
- The checklist of leak fixes in `tradingagents/dataflows/` is a good template for auditing our
  own pipelines.

## Reproduce

No experiment script here: running the pipeline needs paid LLM API keys and live data feeds,
and the point of the findings above is that a historical run would not be a fair test anyway.
Everything above comes from reading `tradingagents/graph/`, `agents/`, `dataflows/`, `memory/`,
`backtest.py` and the changelog in `README.md`.
