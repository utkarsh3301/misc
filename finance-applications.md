# Game Theory Through a Financial Analyst's Lens

A financial analyst mostly meets game theory outside the trading floor: in industry
structure, deal design, capital structure, and the negotiation between management,
shareholders, and creditors. The common thread is that the "right" valuation or
recommendation depends on how other rational parties will respond to it.

## Competitive strategy and industry structure

Porter's five forces is descriptive; the underlying models are game-theoretic
oligopoly:

- **Cournot competition**: firms choose quantities simultaneously, price clears the
  market. Equilibrium quantity per firm falls as the number of competitors rises,
  converging toward the competitive outcome. Useful first pass for capacity-driven
  industries (commodities, semis, airlines).
- **Bertrand competition**: firms choose prices instead of quantities. With
  homogeneous goods and no capacity constraint, just two competitors is enough to
  push price to marginal cost, the "Bertrand paradox." Explains why undifferentiated
  commoditized businesses (execution-only brokerage, plain-vanilla index funds) see
  margins collapse quickly, and why moats matter more than share.
- **Stackelberg competition**: one firm (the leader) commits first, the follower
  best-responds. First-mover commitment can be valuable even though Cournot
  simultaneous play would be more symmetric, this is the formal basis for a lot of
  "first scaled entrant wins" investment theses, but only when the commitment is
  actually irreversible (capacity, exclusive contracts), not just being first to
  announce.
- **Entry deterrence and predatory pricing**: an incumbent's threat to flood the
  market only deters entry if it is credible, i.e. subgame perfect. Excess capacity,
  long-term contracts, or a demonstrated history of punishing entrants are ways
  incumbents make the threat credible. When evaluating a moat, ask whether the
  deterrent is an equilibrium threat or just a stated intention.

## Signaling and screening

Under asymmetric information, one side often cannot directly prove a private fact
(quality, creditworthiness, true earnings power), so it sends a costly signal
instead:

- **Spence signaling** (1973): a signal only works if it is cheaper for the
  high-type to send than for the low-type, otherwise everyone imitates it. Dividend
  initiation, buybacks, and insider buying are classic signals: a company that
  cannot sustain the cash flow suffers more from committing to it, so committing is
  informative. This is why the market reaction to a dividend cut is usually worse
  than the yield math alone implies, it also destroys a signal.
- **Screening**: the uninformed side designs a menu so the informed side
  self-selects and reveals type, e.g. loan covenants, collateral requirements, and
  tiered underwriting are screening devices against adverse selection in credit.

## Adverse selection

Akerlof's "Market for Lemons" (1970): if sellers know more about quality than
buyers, low-quality sellers crowd out high-quality ones unless there is a
countervailing mechanism, potentially collapsing the market entirely.

- **IPO underpricing** is partly a lemons solution: pricing below expected fair
  value compensates uninformed investors for the risk of adverse selection against
  informed ones (Rock, 1986), which is also why underpricing is larger exactly when
  information asymmetry is larger (younger, harder-to-value companies).
- **M&A due diligence** exists because the target always knows more than the
  acquirer; deal structures (earnouts, stock consideration, reps and warranties
  insurance) are mechanisms to reallocate the lemons risk rather than eliminate it.

## Principal-agent problems

Whenever one party (the principal: shareholders, LPs) delegates decisions to another
(the agent: management, the GP) whose effort or information cannot be fully
observed, incentives diverge:

- **Moral hazard**: the agent's effort or risk-taking is unobservable, so
  compensation must be tied to a noisy but verifiable proxy (stock price, realized
  P&L), which is exactly why equity-based comp exists and exactly why it creates its
  own distortions (short-termism, excess risk-taking near payout thresholds, the
  classic "gambling for resurrection" behavior in distressed or underwater managers).
- **Optimal contracting** (Holmstrom, 1979): the informativeness principle says
  compensation should load on any signal that reduces uncertainty about effort, not
  just the most obviously related one, this is the formal justification for relative
  performance evaluation against a peer index rather than an absolute benchmark.

## M&A as a game

- **Auctions and the winner's curse**: in a contested sale with several bidders and
  uncertain common value (synergies, true standalone value), the winning bid is
  the most optimistic estimate, expected to be biased above fair value. Rational
  bidders shade their bids knowing this; the ones who do not overpay systematically.
- **Toeholds and pre-announcement stakes**: an acquirer building a toehold before
  bidding changes the game because it can profit even if it loses the auction to a
  higher bidder, which supports more aggressive bidding and is a standard strategic
  finance lever, not just a legal formality.
- **Poison pills and staggered boards**: commitment devices that change the
  target's payoff structure to make the initial low bid a worse outcome for the
  acquirer than negotiating, functionally identical to any other credible-threat
  device in the entry-deterrence literature above.
- **All-pay dynamics in bidding wars**: once a bidding war becomes about ego, reputation,
  or a deal that must close for career reasons, it starts to resemble an all-pay
  auction (everyone spends the effort/reputation cost, only one gets the prize),
  which is a well documented driver of overpayment.

## Capital structure and bargaining

- **Debt restructuring as Nash bargaining**: the surplus from avoiding a costly
  bankruptcy is split between debt and equity holders roughly according to
  bargaining power (who can better tolerate no deal), which is why restructuring
  outcomes track relative leverage of negotiating position more than any formula.
- **Holdout problem**: in a bond exchange, each individual creditor prefers everyone
  else tenders while they hold out for full recovery, a coordination failure with
  the same structure as a public goods game. Collective action clauses exist purely
  to remove this equilibrium.
- **Sovereign debt games**: repeated interaction with reputational stakes; a
  sovereign's willingness to pay is itself an equilibrium object (default is
  attractive exactly when future market access is not valuable enough to deter it).

## Activist investing

An activist campaign is a repeated, partly public game against incumbent
management: reputation (having won before) is an asset that changes the payoff of
future targets before a single share is bought. "Wolf pack" behavior, several
funds independently building stakes around the same thesis without formal
coordination, is a tacit-coalition equilibrium, valuable specifically because it is
not formal coordination (which would trigger group filing and disclosure
obligations).

## Regulatory and policy games

- **Regulatory arbitrage as a race to the bottom**: if capital can relocate across
  jurisdictions, regulators are themselves playing a game against each other, not
  just against the regulated; unilateral tightening can just export the activity.
- **"Too big to fail" is a commitment problem**: the regulator's ex-ante promise not
  to bail out is not credible ex-post once failure is imminent, and rational
  institutions correctly price that into their risk-taking. This is identical in
  structure to the entry-deterrence credibility problem above, just with the
  regulator as the party unable to commit.

## Real options and strategic investment

An investment opportunity with a "wait and see" option is itself a game if a
competitor holds a similar option: waiting is individually optimal but being
preempted destroys the option's value entirely, which produces classic preemption
races (patent races, spectrum auctions, capacity additions in cyclical industries)
where the equilibrium can involve investing earlier and at a lower expected NPV
than the standalone real-options value would suggest, purely to deny the option to
a rival.

See `foundations.md` for the underlying solution concepts and
`quant-trading-models.md` for the market microstructure and trading-desk lens, with
working simulations.
