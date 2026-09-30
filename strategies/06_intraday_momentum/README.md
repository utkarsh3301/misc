# Strategy 6: Intraday time-series momentum

The most academically-grounded but least India-tested strategy in the
set.

## Specification

Compute r1, the return from the prior close to 09:45 (Nifty's version
of "the first half hour," including the overnight gap). Near 14:45-
14:50, buy an ATM/ITM call if r1 is positive and beyond a threshold
(60th-70th percentile of recent |r1| values); buy a put on the mirror
condition. Trade only on high-volatility, high-volume opening days,
where the literature says the effect concentrates. Time exit at 15:20,
stop at 15-20% of premium.

## Evidence

Gao, Han, Li & Zhou, *Journal of Financial Economics* (2018), SPY 1993-
2013: the first half-hour return predicts the last half-hour return
(scaled slope 6.94, R-squared 1.6%), rising to 2.6% combined with the
second-to-last half hour's return, and to 3.3% on high-volatility days.
Stronger on volatile, high-volume, recession and news days; replicated
in 10 other US ETFs, Chinese markets, and commodity/crude futures. Later
work finds the effect has decayed somewhat in more recent US data.

**No published Nifty-options implementation of this was found.** This
is a direct academic-to-India transfer, untested at the instrument
level used here.

## Probability of profit

Monte Carlo assumption: **54% win rate** (from an R-squared of 1.6-3.3%,
which implies a real but modest directional edge, not a large one), avg
win 10 points / avg loss 8 points, a deliberately small, close-to-even
reward-to-risk to match a modest edge. Result: POP over 250 trades is
around 59%, the least convincing POP of the seven, consistent with this
being the least India-validated strategy in the set. Only one trade at
most per session, so 250 trades is roughly a full trading year.

## Data requirements

1-minute index/futures data, the prior session's close, and first-half-
hour volume. Order frequency (at most one per day) is trivial.

## Option-buying considerations

The short 30-40 minute hold keeps vega exposure low, but theta per
minute is highest late in the session and on expiry day; prefer non-
expiry days or ITM strikes for this one.

## Failure modes

Late-day reversals on quiet days, Tuesday expiry pinning, and closing-
auction mechanics distorting the last-30-minute read. Distinct from and
diversifying to Strategy 3 (ORB): a different time-of-day bucket, and a
signal that explicitly includes the overnight gap that ORB ignores.

## Sources

Gao, Han, Li & Zhou, *Journal of Financial Economics* 151:377-395
(2018), "Market Intraday Momentum". Replications summarised on
Paperswithbacktest and ResearchGate.
