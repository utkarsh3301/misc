# Game Theory Through a Quant Trader's Lens

Where the financial analyst sees game theory in deal design and industry structure,
a quant trader meets it directly in market microstructure: every fill happens
because someone else chose to be on the other side, and market design (tick size,
auction rules, order priority) is a mechanism-design object that shapes who wins.
This doc is the applied, computational companion to `foundations.md`. Working code
for every model below is in `code/`.

## Market making as a repeated game against unknown counterparty type

A market maker quotes a two-sided price without knowing whether the next arrival is
informed (knows something about future value) or uninformed (liquidity/noise
trading). Every quote is a mechanism-design problem: wide enough to survive adverse
selection from informed flow, tight enough to win uninformed flow before a
competitor does. Two models formalize this:

- **Glosten-Milgrom (1985)**: sequential trade model. A specialist sets bid and ask
  using Bayes' rule on the fact of a buy or sell arriving, given a fraction `alpha`
  of traders are informed. Equilibrium spread is pinned down entirely by adverse
  selection, there is no explicit inventory or processing cost in the base model.
  Implemented in `code/glosten_milgrom.py`: spread as a function of `alpha` and of
  the informed trader's signal precision.
- **Kyle (1985)**: batch auction model. A single informed insider with private
  signal `v` submits order size optimally against noise trader flow, and a
  risk-neutral market maker sets a linear price impact `lambda` from the total
  order flow. The insider's optimal trade intensity and the market maker's `lambda`
  are a mutual best response, a Bayesian Nash equilibrium in a single round.
  Implemented in `code/kyle_model.py`, including the classic result that the
  insider trades to reveal exactly half of their private information per period in
  the multi-round extension.

Both models say the same thing in different clothes: the spread, or the price
impact coefficient, is compensation demanded for playing a game against an opponent
whose type you cannot observe. Anything that changes the mix of informed to
uninformed flow (a new disclosure regime, a payment-for-order-flow arrangement that
segregates retail, a latency advantage) moves the equilibrium spread even with zero
change in fundamental volatility.

## Oligopolistic liquidity provision

With multiple market makers quoting the same instrument, competition for order flow
resembles Cournot/Bertrand oligopoly (see `finance-applications.md`), but the choice
variable is depth and spread rather than price and quantity of a single good:

- Treating each maker's quoted size as a Cournot "quantity," more competitors
  quoting compresses the equilibrium spread toward the adverse-selection floor,
  exactly analogous to price converging to marginal cost as competitors are added.
- Unlike a textbook Cournot good, market making has a winner-take-most tie-break
  (price-time priority), which pushes the game closer to Bertrand and helps explain
  why spreads in liquid, multi-maker markets are so thin: undercutting by a
  sub-tick-equivalent (queue position) is nearly free.

`code/cournot_market_makers.py` runs the best-response dynamics for `n` maker
quantity competition and plots how equilibrium aggregate depth and per-maker profit
change as `n` grows, the discrete quant analogue of "why did spreads compress when a
fourth liquidity provider showed up."

## The HFT arms race

Latency competition (colocation, microwave links, FPGA order entry) has the payoff
structure of a war of attrition / all-pay auction: everyone who competes pays the
infrastructure cost, but only the fastest captures the queue-priority or
latency-arbitrage prize. Key implications that follow directly from the all-pay
structure, not from any specific technology:

- Aggregate spend on speed can exceed the size of the arbitrage opportunity being
  competed for, this is a standard all-pay auction result (Budish, Cramton, Shim,
  2015, "The High-Frequency Trading Arms Race"), not a market failure unique to
  finance.
- Their proposed fix, frequent batch auctions instead of continuous-time trading,
  is a mechanism-design response: it converts a continuous speed race into a
  discrete-time auction where being one microsecond faster no longer matters, only
  being inside the batch window does.

## Algorithmic collusion

Independently trained adaptive pricing or quoting agents (reinforcement-learning
market makers, in particular) can converge to tacitly collusive, supra-competitive
spreads without any communication, purely because a repeated-game folk-theorem
equilibrium (see `foundations.md`) is reachable by trial-and-error learning, not
only by explicit reasoning. This is an active regulatory concern (studied
empirically in algorithmic pricing on e-commerce platforms, and directly relevant to
quoting algorithms in less liquid instruments with few active makers).
`code/iterated_prisoners_dilemma.py` runs a round-robin tournament of classic
repeated-game strategies (always defect, always cooperate, tit-for-tat, grim
trigger, win-stay-lose-shift) as the simplest possible model of whether cooperation
(tacit collusion) or competition dominates under repetition, and how sensitive that
is to the discount factor / probability of continued interaction.

## Auction theory in market design

Auctions are everywhere in market structure, not just IPOs:

- **Exchange opening/closing auctions**: uniform-price batch auctions solving for a
  single clearing price that maximizes matched volume, chosen specifically because
  continuous trading at the open would be dominated by stale-quote adverse
  selection after an overnight information gap.
- **Treasury auctions**: uniform-price vs discriminatory ("pay-as-bid") price rules
  change bidder incentives materially; the US Treasury moved to uniform-price for
  exactly the game-theoretic reason that it weakens the winner's-curse shading
  incentive and was found to raise revenue.
- **IPO bookbuilding vs auction (Dutch) IPOs**: bookbuilding gives the underwriter
  discretion to allocate to informed investors in exchange for honest price
  discovery (a screening mechanism), Dutch auction IPOs attempt to let the market
  clear directly; the persistent choice of bookbuilding by issuers is itself
  evidence about which mechanism actually maximizes proceeds net of information
  production.
- **MEV and block auctions in DeFi**: proposer-builder separation is a direct,
  modern instance of mechanism design, splitting the "which transactions get
  included and in what order" decision into an auction specifically to control
  rent extraction (frontrunning/sandwiching) by the block producer.

`code/auctions.py` runs a Monte Carlo comparison of first-price sealed-bid vs
second-price (Vickrey) auctions under independent private values, demonstrating
truthful bidding as a dominant strategy in second-price and the revenue equivalence
theorem numerically (same expected seller revenue under both, despite very
different individual bidding behavior).

## Cooperative game theory on the book

Once a portfolio or trading desk runs multiple correlated strategies or factors,
attributing total P&L or total risk back to each component is exactly the
cooperative game theory allocation problem from `foundations.md`: what is each
strategy's fair share of the joint outcome, accounting for the fact that
diversification means the whole is not simply the sum of parts run in isolation.
The **Shapley value**, each component's average marginal contribution across every
possible order of inclusion, is the standard rigorous answer, and is directly usable
for both risk-factor attribution (how much of portfolio VaR is "caused" by each
position) and multi-strategy P&L splitting in a fund with shared capital and
netting benefits. `code/nash_solver.py` includes a small Shapley value routine
alongside the Nash equilibrium solver, since both are linear-algebra-flavored small
game computations.

## Market ecology and evolutionary dynamics

Which trading styles thrive is not static: it is a population game (see
`foundations.md`, evolutionary game theory). Momentum, mean reversion, market
making, and arbitrage strategies compete for a finite pool of exploitable
inefficiency and each other's order flow; a strategy's realized return depends on
how crowded it currently is, which is exactly replicator dynamics, capital flows
toward whatever just outperformed, compressing that edge, and away from whatever
just underperformed, sometimes right before it recovers. This is the rigorous
version of "the market is reflexive" and "edges decay," worth keeping in mind before
treating any backtested edge as a fixed parameter rather than an equilibrium object
that moves as participation moves.

## Code index

| File | Model | What it demonstrates |
|---|---|---|
| `code/nash_solver.py` | Nash equilibrium (2-player normal form) + Shapley value | Finds pure and mixed equilibria by support enumeration; allocates coalition value fairly |
| `code/kyle_model.py` | Kyle (1985) single-period insider trading | Optimal informed trade intensity and market maker's lambda as a joint fixed point |
| `code/glosten_milgrom.py` | Glosten-Milgrom (1985) sequential trade | Bid-ask spread as a function of the fraction of informed traders |
| `code/cournot_market_makers.py` | Cournot oligopoly applied to depth competition | Equilibrium depth/profit per maker as the number of competing makers grows |
| `code/iterated_prisoners_dilemma.py` | Repeated games / folk theorem | Round-robin tournament of classic strategies, sensitivity to discount factor |
| `code/auctions.py` | First-price vs second-price auctions | Truthful bidding dominance and revenue equivalence via Monte Carlo |

Run any script directly, e.g. `python3 code/kyle_model.py`. See `code/requirements.txt`
for dependencies and `references.md` for the primary sources behind each model.

## Figures

Generated by `code/make_figures.py` (regenerate with `python3 code/make_figures.py`
after changing any model), saved to `figures/`:

| Figure | Shows |
|---|---|
| `figures/glosten_milgrom_spread.png` | Spread vs fraction of informed traders |
| `figures/glosten_milgrom_belief_convergence.png` | Price discovery speed at three informed-trader shares |
| `figures/cournot_spread_and_profit.png` | Spread and per-maker profit compressing as competitors are added |
| `figures/auction_revenue_distribution.png` | First-price vs second-price revenue distributions (equal mean, different shape) |
| `figures/kyle_price_impact.png` | Price impact (lambda) vs noise-trader volume, at three signal-strength levels |
| `figures/ipd_discount_threshold.png` | Cooperation vs defection payoff crossing at the folk-theorem threshold |
