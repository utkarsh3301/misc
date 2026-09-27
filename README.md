

- `foundations.md`: core concepts (equilibrium notions, canonical games, cooperative
  game theory, repeated games, evolutionary game theory, mechanism design).
- `finance-applications.md`: the financial analyst's lens (industry structure, M&A,
  signaling and adverse selection, principal-agent problems, capital structure,
  activist investing, regulation, real options).
- `quant-trading-models.md`: the quant trader's lens (market making, information
  asymmetry, oligopolistic liquidity provision, the HFT arms race, algorithmic
  collusion, auction-based market design, risk/P&L attribution, market ecology),
  backed by working, numerically verified code.
- `code/`: runnable Python for six of the core models (Nash equilibrium and
  Shapley value solver, Kyle model, Glosten-Milgrom, Cournot depth competition,
  iterated prisoner's dilemma, first vs second price auctions). Each script
  verifies its own theory against simulation when run.
- `figures/`: plots generated from the code, referenced from `quant-trading-models.md`.
- `references.md`: primary sources.

Run any model with `python3 code/<script>.py` (see `code/requirements.txt`), and
regenerate figures with `python3 code/make_figures.py`.
