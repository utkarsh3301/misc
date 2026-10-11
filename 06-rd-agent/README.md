# 06. Microsoft RD-Agent(Q) (LLM agent that mines factors)

Repo: https://github.com/microsoft/RD-Agent
Paper: R&D-Agent-Quant, arXiv 2505.15155 (NeurIPS 2025)
Studied: shallow clone of `main`, October 2026.

## What it is

An LLM "research and development" loop built on top of qlib. The agent proposes a hypothesis
("stocks with rising turnover and falling volatility outperform"), writes the factor code, runs
a qlib backtest with the new factor added to its library, reads the result, and decides whether
to keep it. The README claims that "at a cost under $10, RD-Agent(Q) achieves approximately 2x
higher ARR than benchmark factor libraries while using over 70% fewer factors."

## How it works (from the source)

| Piece | File | Detail |
|---|---|---|
| Loop settings | `rdagent/app/qlib_rd_loop/conf.py` | Train 2008-2014, valid 2015-2016, test 2017-01-01 to 2020-08-01, CSI300. The same split as qlib's benchmarks. |
| Backtest config | `rdagent/scenarios/qlib/experiment/factor_template/conf_combined_factors.yaml` | `backtest.start_time: {{ test_start }}`, `end_time: {{ test_end }}`. The portfolio backtest and IC are computed on the test segment. |
| Feedback | `rdagent/scenarios/qlib/developer/feedback.py` | `IMPORTANT_METRICS = ["IC", "1day.excess_return_with_cost.annualized_return", "1day.excess_return_with_cost.max_drawdown"]`. These test-segment numbers for the new run and the current best are pasted into the LLM prompt. |
| Decision | `rdagent/scenarios/qlib/prompts.yaml` | The LLM answers `"Replace Best Result": "yes or no"`. The prompt instructs: "Any small improvement should be considered for inclusion as SOTA". Accepted factors join the library for every later round. |

## Where the edge is supposed to come from

An LLM can propose economically motivated factors faster than a human, and an evolving library
keeps only the ones that help.

## What I found

**1. Factors are selected on the test period.** As shipped, the number the loop climbs is the
2017 to mid-2020 IC and excess return, which is also the period the final result is reported
on. There is a validation segment (2015 to 2016), but it is used only by the model for early
stopping, not by the agent to accept factors. Each "yes" is a small fit to the test set; after
dozens of rounds the library is tuned to that window.

**2. How much of the gain selection alone can produce.** I replaced the LLM with a proposer that
knows nothing: it draws random price/volume formulas (rolling returns, averages, volatility,
highs, lows, volume ratios, price-volume correlation, random windows and signs), and keeps one
whenever the combined signal's rank IC on 2017-01 to 2020-07 improves, i.e. RD-Agent's
acceptance rule. Then I scored the final library on periods the loop never saw. Real CSI300
data, point-in-time membership.

| Proposer | Kept | Rank IC on selection window | 2015-2016 (unseen) | 2020-08 to 2021-05 (unseen) |
|---|---|---|---|---|
| Random formulas | 12 of 80 | +0.032 | +0.026 | +0.023 |
| Pure noise | 22 of 80 | +0.013 | -0.000 | -0.009 |

- Noise "factors" with zero information built a library that looks like it has IC 0.013 on the
  window it was chosen on, and nothing anywhere else.
- Random formulas carry real signal (mostly short-term reversal, see 01-qlib), but 20 to 30% of
  their apparent IC on the selection window does not carry over (0.032 vs 0.026 and 0.023).

An LLM proposer is far better than random, but it faces the same arithmetic: the more rounds
you accept on the test window, the more of the reported improvement is the window.

**3. The baseline it beats is soft.** The comparison is against "benchmark factor libraries"
(Alpha158, Alpha360) run through a fixed model. In qlib's own table those libraries reach most of
their IC with a linear model (01-qlib), and their own edge has been decaying since 2017 (rank IC
0.058 in 2017 to about 0.02 to 0.03 in 2019 to 2021 in my replication). "2x the ARR" of a decaying
baseline on its own test window is a modest bar.

**4. The cheap part is real.** Under $10 of LLM calls to propose, code and test dozens of factors
is a genuine productivity gain. The code-writing and debugging loop (`developer/`, `coder/`) is
the best engineered part of the project.

## The edge, in one line

A very efficient factor-idea generator, wrapped in an acceptance rule that grades itself on the
test set. Treat its reported returns as in-sample until re-run with selection moved to a
validation window and the test window locked away.

## Takeaways for our own work

- Any agent loop (LLM or not) that reads a metric and keeps what improves it must read that
  metric on validation data. The test window gets opened once, at the end.
- Count the number of trials. A factor that won 1 of 80 rounds needs a much higher bar than a
  factor tested once (deflated Sharpe, or a simple holdout of a later period).
- Run the same loop with a noise proposer as a control. The gap between its in-sample score and
  zero is your selection bias.

## Reproduce

```
curl -L -o cn.zip https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_simple_cn_1d_latest.zip
unzip cn.zip -d cn
python experiments/greedy_test_set_selection.py ./cn
```

The control experiment uses a linear equal-weight combination of z-scored factors instead of
RD-Agent's LightGBM, so it isolates the selection effect rather than replicating the full system.
