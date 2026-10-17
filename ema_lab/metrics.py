"""
Performance statistics for engine results.

"Success percentage" in this repo means the share of closed trades whose
return after costs is above zero (win rate). Win rate alone says little:
trend following rules routinely win 30-40% of trades and still make
money because winners are several times larger than losers, so every
table also reports profit factor and expectancy per trade.
"""

import numpy as np
import pandas as pd


def max_consecutive(mask):
    best = run = 0
    for m in mask:
        run = run + 1 if m else 0
        best = max(best, run)
    return best


def trade_stats(trades):
    n = len(trades)
    if n == 0:
        return {"trades": 0, "win_rate": np.nan, "avg_win": np.nan, "avg_loss": np.nan,
                "payoff": np.nan, "profit_factor": np.nan, "expectancy": np.nan,
                "median_trade": np.nan, "avg_bars": np.nan, "max_consec_losses": 0}
    r = trades["ret"].to_numpy()
    wins, losses = r[r > 0], r[r <= 0]
    gross_win, gross_loss = wins.sum(), -losses.sum()
    return {
        "trades": n,
        "win_rate": len(wins) / n,
        "avg_win": wins.mean() if len(wins) else 0.0,
        "avg_loss": losses.mean() if len(losses) else 0.0,
        "payoff": (wins.mean() / -losses.mean()) if len(wins) and len(losses) and losses.mean() < 0 else np.nan,
        "profit_factor": gross_win / gross_loss if gross_loss > 0 else np.inf,
        "expectancy": r.mean(),
        "median_trade": float(np.median(r)),
        "avg_bars": trades["bars"].mean(),
        "max_consec_losses": max_consecutive(r <= 0),
    }


def daily_returns(returns):
    """Compound bar returns into calendar-day returns."""
    if len(returns) == 0:
        return returns
    day = returns.index.normalize()
    if day.is_unique:
        return returns
    log = np.log1p(returns.to_numpy())
    codes, uniques = pd.factorize(day)
    summed = np.bincount(codes, weights=log, minlength=len(uniques))
    return pd.Series(np.expm1(summed), index=uniques)


def equity_stats(returns):
    returns = returns.fillna(0.0)
    daily = daily_returns(returns)
    equity = (1.0 + daily).cumprod()
    years = max((daily.index[-1] - daily.index[0]).days / 365.25, 1e-9)
    periods = len(daily) / years
    total = equity.iloc[-1] - 1.0
    cagr = equity.iloc[-1] ** (1.0 / years) - 1.0 if equity.iloc[-1] > 0 else -1.0
    sd = daily.std()
    sharpe = daily.mean() / sd * np.sqrt(periods) if sd > 0 else np.nan
    downside = daily[daily < 0].std()
    sortino = daily.mean() / downside * np.sqrt(periods) if downside > 0 else np.nan
    drawdown = equity / equity.cummax() - 1.0
    mdd = drawdown.min()
    return {
        "total_return": total,
        "cagr": cagr,
        "vol": sd * np.sqrt(periods),
        "sharpe": sharpe,
        "sortino": sortino,
        "max_dd": mdd,
        "calmar": cagr / -mdd if mdd < 0 else np.nan,
        "years": years,
    }


def summarize(result, df=None, start=None):
    """
    One flat dict of trade, equity and (optionally) buy and hold stats.
    start limits every statistic, including buy and hold, to bars from
    that timestamp on, so rules whose indicators need a long warm-up are
    not compared against a benchmark that was invested during it.
    """
    returns, position, trades = result.returns, result.position, result.trades
    if start is not None:
        returns, position = returns.loc[start:], position.loc[start:]
        trades = trades[trades.entry_time >= start]
    out = trade_stats(trades)
    out.update(equity_stats(returns))
    out["exposure"] = float((position != 0).mean())
    out["trades_per_year"] = out["trades"] / out["years"] if out["years"] > 0 else np.nan
    if df is not None:
        bh = equity_stats(df["close"].pct_change().fillna(0.0).loc[returns.index[0]:])
        out["bh_cagr"] = bh["cagr"]
        out["bh_sharpe"] = bh["sharpe"]
        out["bh_max_dd"] = bh["max_dd"]
    return out


def with_carry(result, cash_rate=0.06, div_yield=0.013, periods=252):
    """
    Bar returns plus interest on idle capital and dividends while long.
    Price-only backtests understate rules that sit in cash: an Indian
    liquid fund or overnight TREPS paid roughly 5-7% a year over this
    period, while Nifty's dividend yield was about 1.3%. Shorts pay the
    dividend instead of receiving it. Use only on daily bars.
    """
    pos = result.position.to_numpy()
    carry = np.where(pos == 0, cash_rate, pos * div_yield) / periods
    return result.returns + carry


def yearly_returns(returns):
    daily = daily_returns(returns.fillna(0.0))
    return (1.0 + daily).groupby(daily.index.year).prod() - 1.0
