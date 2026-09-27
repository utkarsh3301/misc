# Game Theory: Foundations

Game theory is the study of strategic interaction: situations where the outcome for
each participant depends not only on their own choices but on the choices of others.
It sits between economics, mathematics, and computer science, and it is the
mathematical backbone for almost everything in markets that involves more than one
self-interested party: pricing, negotiation, market making, auctions, and regulation.

The distinguishing feature versus ordinary optimization is that you cannot just
maximize against a fixed environment. The environment (the other players) is also
optimizing, and is often optimizing against your expected behavior. This is what
makes markets fundamentally game-theoretic rather than purely statistical.

## Core primitives

Every game is defined by:

- **Players**: the decision makers (traders, firms, bidders, regulators, even
  algorithms).
- **Actions / strategies**: a strategy is a full contingency plan, not just a single
  move. A *pure* strategy picks one action deterministically; a *mixed* strategy is a
  probability distribution over actions.
- **Information**: what each player knows when they act (their own type, history of
  play, signals about others). Games of *complete information* mean payoffs are
  common knowledge; *incomplete information* means players have private information
  (types), handled with Bayesian games.
- **Payoffs**: a utility function mapping the full action profile (one action per
  player) to a real number for each player. In finance this is usually P&L, but risk
  aversion means it is often a utility function of P&L, not P&L itself.

## Representing games

- **Normal form**: a payoff matrix (or tensor for >2 players). Good for static,
  simultaneous-move games.
- **Extensive form**: a game tree with decision nodes, information sets, and
  terminal payoffs. Needed whenever timing, sequencing, or observability matters,
  which is most of real market interaction (quote, then observe, then trade).

## Solution concepts

- **Dominant strategy**: a strategy that is best regardless of what others do. Rare
  in interesting games, but powerful when it exists (e.g. truthful bidding in a
  second-price auction).
- **Nash equilibrium**: a strategy profile where no player can improve their payoff
  by unilaterally deviating, given what everyone else is playing. Every finite game
  has at least one Nash equilibrium in mixed strategies (Nash, 1950). This is the
  workhorse solution concept: it does not require players to be right about the
  future, only that nobody regrets their choice given what actually happened.
- **Subgame perfect equilibrium** (Selten, 1965): a Nash equilibrium that also
  requires optimal play in every subgame, ruling out threats that would not actually
  be carried out. Solved by backward induction. This matters in trading whenever a
  strategy depends on a threat or commitment (e.g. "I will always undercut you if you
  deviate") that needs to be credible to work.
- **Bayesian Nash equilibrium** (Harsanyi, 1967-68): the equivalent for games of
  incomplete information, where players have private types drawn from a known
  distribution and best-respond in expectation over others' types. This is the
  natural framework for markets, since counterparties' information and inventory are
  rarely observable.
- **Perfect Bayesian / sequential equilibrium**: combines the two, needed for dynamic
  games with private information, e.g. a market maker updating beliefs about whether
  the last trade was informed.

## Canonical games worth memorizing

| Game | Structure | Lesson |
|---|---|---|
| Prisoner's Dilemma | Mutual cooperation beats mutual defection, but defection dominates individually | Individually rational choices can be collectively suboptimal; underlies collusion, price wars, tragedy of the commons |
| Matching Pennies | Zero-sum, no pure equilibrium | Pure mixed-strategy play is sometimes correct, not evasive; relevant to order routing / randomized execution |
| Battle of the Sexes | Two coordination equilibria, players disagree on which | Coordination problems need a focal point or communication; relevant to standards, exchange choice |
| Stag Hunt | Cooperative equilibrium payoff-dominates but is riskier | Trust and risk-dominance can block a superior equilibrium; relevant to liquidity coordination (self-fulfilling illiquidity) |
| Hawk-Dove / Chicken | Aggressive-aggressive is worst outcome for both | Models entry deterrence, price wars, and the HFT "who blinks first" dynamic |

## Zero-sum games and minimax

In a two-player zero-sum game, one player's gain is the other's loss exactly. Von
Neumann's minimax theorem (1928) guarantees a value of the game and optimal mixed
strategies solvable by linear programming: maximize your guaranteed payoff assuming
the opponent plays your worst case. Most retail intuitions about "the market is
zero-sum" are wrong for markets in aggregate (trading creates and destroys risk,
financing has real economic surplus), but specific sub-games *are* effectively
zero-sum: a single order crossing the spread against a market maker, one arbitrageur
racing another for the same mispricing, or a fixed-size options market with matched
notional.

## Cooperative game theory

Non-cooperative theory (above) assumes players cannot make binding agreements.
Cooperative game theory instead studies which coalitions form and how they split
value:

- **Characteristic function**: v(S), the value achievable by any coalition S acting
  alone.
- **The core**: the set of allocations no coalition can improve upon by breaking
  away. Can be empty.
- **Shapley value** (Shapley, 1953): the unique allocation satisfying efficiency,
  symmetry, and additivity, splitting value by each player's average marginal
  contribution across all possible orderings. This is directly usable for P&L and
  risk attribution across a portfolio or a multi-strategy book, see
  `quant-trading-models.md`.
- **Nash bargaining solution** (Nash, 1950): the unique split of a bargaining surplus
  satisfying a small set of fairness axioms, maximizing the product of gains over the
  disagreement point. Useful for OTC negotiation and block trade pricing.

## Repeated games

A stage game played many times changes the equilibrium set entirely. The **Folk
Theorem** says that if players are patient enough (discount factor close to 1), any
individually rational payoff (including full cooperation) can be sustained as an
equilibrium of the repeated game, supported by trigger strategies: cooperate until
someone defects, then punish. This is the formal basis for:

- Tacit collusion between market makers or dealers without explicit communication.
- Reputation effects (a dealer who reneges on a quote loses future flow).
- Why regulators worry about repeated interaction among a small number of liquidity
  providers, algorithmic or human.

## Evolutionary game theory

Instead of assuming rational optimization, evolutionary game theory asks which
strategies survive selection pressure in a population. An **evolutionarily stable
strategy** (Maynard Smith and Price, 1973) cannot be invaded by a rare mutant
strategy. **Replicator dynamics** model how the population share of each strategy
grows in proportion to its relative payoff. This maps well onto market ecology: which
trading styles (momentum, mean reversion, market making, arbitrage) persist,
proliferate, or get crowded out and go extinct as capital reallocates toward
whatever is currently profitable.

## Mechanism design

Mechanism design is game theory in reverse: instead of taking the rules of the game
as given and solving for equilibrium behavior, you design the rules so that
equilibrium behavior produces a desired outcome, even though every participant is
still just pursuing self-interest.

- **Revelation principle**: any outcome implementable by some mechanism can be
  implemented by a direct mechanism where truth-telling is optimal, which is why
  incentive-compatibility is the central design constraint.
- **Incentive compatibility (IC)**: no player wants to misreport their private
  information.
- **Individual rationality (IR)**: no player is worse off participating than not.
- **VCG mechanism** (Vickrey-Clarke-Groves): a general construction making truthful
  reporting a dominant strategy by charging each player their externality on others.
  Second-price auctions are the single-item special case.

This is exactly the toolkit exchanges, clearinghouses, and auction designers (IPO
bookbuilding, Treasury auctions, DeFi block-builders) use, and it is the toolkit you
want when designing an execution algorithm, a request-for-quote protocol, or an
internal crossing network.

See `finance-applications.md` for the corporate/strategic finance lens and
`quant-trading-models.md` for the market microstructure lens, with working code.
