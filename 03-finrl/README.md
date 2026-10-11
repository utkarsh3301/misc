# 03. FinRL (deep reinforcement learning for stock trading)

Repo: https://github.com/AI4Finance-Foundation/FinRL
Studied: shallow clone of `master`, October 2026.

## What it is

FinRL wraps standard deep RL algorithms (PPO, A2C, DDPG, TD3, SAC from stable-baselines3) around
a stock-trading "gym" environment. The flagship tutorial trains agents on the Dow 30, then shows
the agents beating the DJIA and a mean-variance portfolio in a 2020-07-01 to 2021-10-29 test
window.

## How it works (from the source)

The core is `finrl/meta/env_stock_trading/env_stocktrading.py` (`StockTradingEnv`).

| Piece | What the code does |
|---|---|
| State | `[cash, close of each stock, shares held of each stock, indicators...]` for today. |
| Action | One number in [-1, 1] per stock, multiplied by `hmax` (100 in the tutorial) and cast to `int`. It is a number of shares, not a weight. |
| Order of fills | All sells first (clipped to shares you own), then buys (clipped to cash you have), at today's close, the same close the agent just saw. |
| Costs | 0.1% each way in the tutorial. |
| Reward | Change in total account value from today to tomorrow, times `reward_scaling` (1e-4). |
| Risk switch | If the risk indicator is at or above `turbulence_threshold`, every position is liquidated and buying is blocked. The NeurIPS 2018 backtest notebook uses `risk_indicator_col='vix'` with threshold 70. |
| Turbulence index | `preprocessors.py`: a Mahalanobis distance of today's returns from the past 252 days. Computed point in time; no look-ahead. |

## Where the edge is supposed to come from

The agent is supposed to learn when to buy, sell and hold each stock from price and indicator
history, plus a crash switch that moves to cash in turbulent markets.

## What I found

**1. The environment pushes any policy toward being fully long.** Sells are clipped to what you
own, buys are clipped only by cash. So a policy with symmetric, meaningless actions still ends up
accumulating stock: you can never sell more than you have, but you keep buying until cash runs
out. In my port of the step logic, agents taking uniform random actions ended windows with a
median of 100% of capital in stocks.

**2. A random agent tracks the market almost perfectly.** I ran the exact FinRL fill rules on
30 large CSI300 stocks, over 49 rolling windows the same length as the tutorial's test window
(about 335 trading days), 2008 to 2021:

| Measure | Result |
|---|---|
| Correlation of the random agents' median return with buy-and-hold, across windows | 0.96 |
| Windows where the best of 20 random agents beats equal-weight buy-and-hold | 80% |
| Windows where the median random agent beats buy-and-hold | 10% |
| Typical gap, median random agent minus buy-and-hold | -5.3 points |
| Buy-and-hold return, worst to best window | -44% to +92% |

So the window you test on decides almost everything. And if you train a handful of agents and
look at the best one in the test window (the NeurIPS 2018 backtest notebook plots A2C, DDPG, PPO,
TD3 and SAC side by side against the DJIA), "one of them beats the index" is the expected outcome
even with zero skill. FinRL's ensemble strategy at least picks among the five by validation-period
Sharpe, which is the right way round, but validation windows of a few months are just as noisy.

**3. The flagship test window is one of the strongest bull runs on record.** July 2020 to
October 2021 was the post-Covid rally. A long-biased agent looks brilliant there, and the VIX 70
crash switch never fires in that window (VIX stayed well under 70 after spring 2020). The
safeguard that is supposed to be the risk edge is dormant during the reported test.

**4. The threshold is set with hindsight.** VIX at or above 70 happened essentially in two
episodes: late 2008 and March 2020. A threshold that only those two crashes clear was chosen by
someone who knew when they happened.

**5. Same-bar fills.** The agent observes today's close and trades at that close. Real orders
can only get near that price with a market-on-close order sent before the close is known. The
bias is small per trade but it is systematic.

**6. A latent tradability hack.** `_sell_stock` and `_buy_stock` check
`self.state[index + 2 * self.stock_dim + 1] != True` "to check if the stock is able to sell".
That slot is not a flag, it is the first technical indicator of that stock (MACD in the
tutorial). A comment says it was put there "for simplicity". If MACD ever equals exactly 1.0,
that stock silently becomes untradeable.

## The edge, in one line

There is no stock-selection edge to find in the environment itself: returns are long-equity
beta plus the luck of the test window, and the risk switch is a hindsight-tuned crash filter
that does nothing in the reported period. The real contribution is a convenient, well-packaged
RL sandbox.

## Takeaways for our own work

- Before training any RL agent, run a random-action agent and an always-buy agent through the
  same environment. Report the agent's result as a percentile of that distribution.
- Test across many windows, including crashes and sideways years, never one bull run.
- Define actions as target weights, not share counts, so the action space is symmetric and the
  policy can actually choose to be flat.

## Reproduce

```
curl -L -o cn.zip https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_simple_cn_1d_latest.zip
unzip cn.zip -d cn
python experiments/random_agent_baseline.py ./cn
```

The script is a direct port of `StockTradingEnv.step`, `_buy_stock` and `_sell_stock` (same
`hmax`, cost, sell-before-buy order, integer shares). It uses 30 Chinese large caps instead of
the Dow 30 because that is the daily data this environment could reach; the mechanics being
tested do not depend on the market.
