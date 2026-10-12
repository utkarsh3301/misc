"""Design A harness: systematic index put-writing on a normalized option chain.

STATUS: written and unit-tested on a small hand-built fixture whose answers are computed by hand
(tests/test_putwrite.py). It has NEVER been run on market data because no option-chain data were
available in the study environment. Nothing in it is tuned: target days to expiry, target delta and
the fill model are inputs fixed before looking at any result.

Normalized chain, one row per option quote:
  quote_date, expiry, strike, cp ('C' or 'P'), bid, ask,
  and either `delta`, or both `iv` and `underlying` (a Black-Scholes delta is then computed).
Settlement: a pd.Series indexed by expiry date holding the settlement value the contract used. For
AM-settled SPX monthlies this is the special opening quotation, not the close, so supply the right series.
Rates: a float (annual, simple) or a pd.Series indexed by date, used for interest on the cash collateral.

Rules (Design A in REPORT.md): on each entry day sell one put whose expiry is closest to target_dte
(at least min_dte) and whose absolute delta is closest to target_delta; fill at the bid (or the mid);
hold to expiry; collateral equals strike times the multiplier, earning the entry-day cash rate; the next
entry is the first quote date on or after the expiry. The return of a trade is
(premium - intrinsic at settlement) * multiplier less fees, divided by collateral, plus interest.
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

from . import index_compare as ic


def bs_put_delta(spot, strike, t_years, rate, div_yield, iv):
    """Black-Scholes put delta (negative), continuous dividend yield."""
    d1 = (np.log(spot / strike) + (rate - div_yield + 0.5 * iv ** 2) * t_years) / (iv * np.sqrt(t_years))
    return float(np.exp(-div_yield * t_years) * (norm.cdf(d1) - 1.0))


def _abs_delta(day, entry_date, rate_for_delta, div_yield):
    """Absolute put delta: the vendor delta where present, a Black-Scholes delta from iv and underlying elsewhere."""
    out = day["delta"].abs() if "delta" in day.columns else pd.Series(np.nan, index=day.index)
    missing = out.isna()
    if missing.any() and {"iv", "underlying"}.issubset(day.columns):
        t = ((day["expiry"] - entry_date).dt.days / 365.0).clip(lower=1e-6)
        for i in day.index[missing]:
            iv, u = day.at[i, "iv"], day.at[i, "underlying"]
            if pd.notna(iv) and pd.notna(u) and iv > 0:
                out.at[i] = abs(bs_put_delta(u, day.at[i, "strike"], t.at[i], rate_for_delta, div_yield, iv))
    return out


def _rate_on(rates, date):
    if isinstance(rates, pd.Series):
        return float(rates.asof(date))
    return float(rates)


def put_write_backtest(
    chain,
    settlement,
    rates,
    target_dte=35,
    target_delta=0.16,
    min_dte=7,
    fill="bid",
    fee_per_contract=0.0,
    multiplier=100,
    div_yield=0.0,
    root=None,
):
    """Return a DataFrame with one row per trade.

    root: if given and the chain has a `root` column (for example SPX versus SPXW), keep only that root so that
    AM and PM settled series sharing a strike and expiry are not mixed.
    """
    if fill not in ("bid", "mid"):
        raise ValueError("fill must be 'bid' or 'mid'")
    chain = chain.copy().reset_index(drop=True)  # unique labels even if files were concatenated
    chain["quote_date"] = pd.to_datetime(chain["quote_date"])
    chain["expiry"] = pd.to_datetime(chain["expiry"])
    if root is not None and "root" in chain.columns:
        chain = chain[chain["root"] == root]
    puts = chain[chain["cp"] == "P"]
    by_day = {pd.Timestamp(k): g for k, g in puts.groupby("quote_date")}  # one pass over the chain, not one scan per date
    trades = []
    next_entry = pd.Timestamp.min
    for d in sorted(by_day):
        if d < next_entry:
            continue
        day = by_day[d]
        dte = (day["expiry"] - d).dt.days
        day = day[dte >= min_dte]
        if fill == "bid":
            day = day[day["bid"] > 0]
        else:
            day = day[(day["bid"] > 0) & (day["ask"] > 0)]
        if day.empty:
            continue
        exps = day["expiry"].drop_duplicates().sort_values()
        gaps = ((exps - d).dt.days - target_dte).abs()
        ex = exps.iloc[int(np.argmin(gaps.values))]
        if ex not in settlement.index:
            continue
        sub = day[day["expiry"] == ex]
        rate = _rate_on(rates, d)
        ad = _abs_delta(sub, d, rate, div_yield).dropna()
        if ad.empty:
            continue
        pick = sub.loc[(ad - target_delta).abs().idxmin()]
        premium = float(pick["bid"]) if fill == "bid" else float((pick["bid"] + pick["ask"]) / 2.0)
        strike = float(pick["strike"])
        s_t = float(settlement.loc[ex])
        loss = max(strike - s_t, 0.0)
        days = int((ex - d).days)
        pnl = (premium - loss) * multiplier - fee_per_contract
        ret = pnl / (strike * multiplier) + rate * days / 365.0
        trades.append(
            {
                "entry": d,
                "expiry": ex,
                "strike": strike,
                "premium": premium,
                "settlement": s_t,
                "days": days,
                "return": ret,
            }
        )
        next_entry = ex
    return pd.DataFrame(trades)


def evaluate(trades, benchmark_index, rf_annual=0.0, hac_lags=3):
    """Compare trade returns with a benchmark index held over the same entry and expiry dates.

    benchmark_index: pd.Series of index LEVELS (ideally total return) indexed by date.
    """
    bench = [
        float(benchmark_index.asof(e) / benchmark_index.asof(s) - 1.0)
        for s, e in zip(trades["entry"], trades["expiry"])
    ]
    ppy = 365.25 / float(trades["days"].mean())
    strat = pd.Series(trades["return"].values, index=trades["entry"].values)
    bm = pd.Series(bench, index=trades["entry"].values)
    res = ic.compare(strat, bm, rf_annual=rf_annual, periods_per_year=ppy, hac_lags=hac_lags)
    res["trades"] = {
        "n": int(len(trades)),
        "mean_days": float(trades["days"].mean()),
        "periods_per_year": float(ppy),
        "win_rate": float((trades["return"] > 0).mean()),
        "mean_return": float(trades["return"].mean()),
        "worst_trade": float(trades["return"].min()),
    }
    return res


OPTIONSDX_PUT_COLUMNS = {
    "p_bid": "bid",
    "p_ask": "ask",
    "p_delta": "delta",
    "p_iv": "iv",
    "underlying_last": "underlying",
    "expire_date": "expiry",
}


def load_chain(path, fmt="normalized", colmap=None):
    """Read a chain CSV into the normalized layout.

    fmt "normalized": the file already has the normalized column names.
    fmt "optionsdx": one row per strike with c_* and p_* columns (column layout RECALLED from the vendor's public
    description, not checked against a real file; pass colmap to adapt). Names are lower-cased and stripped of
    brackets and spaces before mapping.
    """
    df = pd.read_csv(path)
    df.columns = [str(c).strip().strip("[]").strip().lower() for c in df.columns]
    if fmt == "optionsdx":
        df = df.rename(columns=OPTIONSDX_PUT_COLUMNS)
        df["cp"] = "P"
    if colmap:
        df = df.rename(columns=colmap)
    return df
