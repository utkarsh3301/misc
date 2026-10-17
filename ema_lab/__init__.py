"""
EMA crossover and candlestick price action research on real market data.

Modules:
    data        loaders for the datasets built by scripts/fetch_data.py
    indicators  EMA, ATR, ADX, RSI, MACD
    patterns    rule based candlestick pattern detection
    costs       per market transaction cost assumptions
    engine      bar by bar backtester (next bar open fills, stops, targets)
    metrics     trade and equity statistics
    strategies  signal builders for every strategy tested
    stats       significance tests (bootstrap, random entry, binomial)
    report_utils  tables, markdown and chart style for the experiment scripts
"""
