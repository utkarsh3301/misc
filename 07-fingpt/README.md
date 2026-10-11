# 07. FinGPT (open financial LLMs: sentiment and the Forecaster)

Repo: https://github.com/AI4Finance-Foundation/FinGPT
Studied: shallow clone of `master`, October 2026.

## What it is

A family of LoRA fine-tunes of open LLMs (Llama 2, ChatGLM2, Qwen and others) for finance. The
two parts that touch trading are:

- **Sentiment models (v3.x):** classify a headline or tweet as positive, negative or neutral.
  The README table shows FinGPT v3.3 beating BloombergGPT and GPT-4 on weighted F1 for the
  standard datasets (FPB 0.882, FiQA-SA 0.874, TFNS 0.903), trained for about $17 on one RTX 3090.
- **FinGPT-Forecaster:** given a company profile, the last 1 to 3 weeks of news and basic
  financials, predict next week's move as a bin such as "up 2-3%" or "down more than 5%", with
  a written analysis. Released after fine-tuning Llama-2-7B on Dow 30 data from 2022-12-30 to
  2023-09-01.

## How the Forecaster is built (from the source)

| Step | File | What happens |
|---|---|---|
| Labels | `fingpt/FinGPT_Forecaster/data.py` (`get_returns`, `bin_mapping`) | Daily adjusted closes resampled to weekly (`'W'`). Return binned: `U`/`D` plus `ceil(abs(100*ret))`, capped at `5+`. So U1 means up 0-1%. |
| Training prompts | `prompt.py` (`get_all_prompts`, `PROMPT_END`) | Past weeks of news and price moves, then: "let's assume your prediction for next week ... is {prediction}. Provide a summary analysis to support your prediction." |
| Training answers | `data.py` (`query_gpt4`) | GPT-4 is called with that prompt, where `{prediction}` is the **actual** next-week bin. Its answer becomes the training target. |
| Fine-tune | `train_lora.py` | LoRA on Llama-2-7B-chat to reproduce GPT-4's answers from the same inputs, without the true bin. |

## Where the edge is supposed to come from

News moves prices, and a fine-tuned LLM can read news faster and more consistently than people.

## What I found

**1. The training targets are hindsight rationalisations.** GPT-4 is told what happened next
week and asked to write an analysis that "supports" it. The student model then learns to
produce that style of analysis without being told the answer. That is a legitimate way to
distil a format, but the reasoning text in the training data is a story written backwards from
the outcome, so the explanations the Forecaster gives should be read as fluent, not as causal.

**2. Weekly direction is mostly the market, and the base rate swings by year.** On CSI300 stocks
(weekly closes, the same resampling the Forecaster uses):

| Year | "Always up" accuracy | Accuracy if you knew the index direction |
|---|---|---|
| 2007 | 62.5% | 70.8% |
| 2008 | 42.7% | 76.8% |
| 2011 | 42.3% | 75.8% |
| 2014 | 54.9% | 70.2% |
| 2019 | 53.1% | 71.1% |
| 2021 (to June) | 48.5% | 55.0% |

In 56% of weeks, more than 70% of stocks moved the same way. A forecaster trained on a rising
period (the Dow ended the 2023 training window higher than it started) learns "up" as a prior and will look accurate on the same kind of
period. Any accuracy figure needs the "always up" and "follow the market" baselines next to it.

**3. The sample is small.** About 30 stocks x 35 weeks is roughly 1,000 training examples. An
accuracy near 55% measured on that many stock-weeks has a standard error of about 1.5 points, and
stock-weeks in the same week are strongly correlated (see point 2), so the effective sample is
closer to the number of weeks, about 35.

**4. Sentiment F1 is not a trading result.** The sentiment table measures agreement with human
labels on headlines. It says nothing about whether the label arrives before the price moves.
Headline sentiment in liquid large caps is typically priced within minutes; a model that reads
it accurately an hour later has an F1 score, not an edge.

**5. The labels have a small, harmless quirk.** `bin_mapping` treats a return of exactly 0 as
"up" (`'U' if ret >= 0`), and `pct_change` on weekly closes measures Friday to Friday, so a
holiday-shortened week is compared with a full one. Neither matters much, but both are worth
knowing before training on the same pipeline.

## The edge, in one line

Cheap, competent financial text classification and a nicely formatted weekly opinion
generator. No evidence of a trading edge in the repo: the Forecaster's targets are written with
hindsight and its natural accuracy baseline is the market's own direction.

## Takeaways for our own work

- For any directional forecaster, report accuracy next to "always up" and "follow the index".
  The second one is the real bar for stock-specific skill.
- Think of the effective sample as the number of independent time periods, not stock-periods.
- If we use LLM sentiment on Indian news, timestamp everything to the minute and test the
  signal against the price move after the headline, not on the same day.

## Reproduce

```
curl -L -o cn.zip https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_simple_cn_1d_latest.zip
unzip cn.zip -d cn
python experiments/weekly_direction_baselines.py ./cn
```

No LLM runs here. The findings on how the Forecaster is trained come from reading
`fingpt/FinGPT_Forecaster/data.py`, `prompt.py` and the README.
