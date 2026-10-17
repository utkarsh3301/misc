"""
Signal builders. Each returns a dict for engine.run().

EMA family:
    ema_cross            fast EMA vs slow EMA, state based (always in the
                         market for long_short, in or flat for long_only)
    ema_cross_filtered   enter on the cross only when filters agree
                         (200 EMA regime, ADX), optional ATR stop/target/trail
    triple_ema           fast > mid > slow alignment
    macd_cross           MACD line vs signal line
    price_vs_ema         close above/below one EMA
    fixed_point_scalper  the original 9/21 one-minute idea from the algo
                         branch: cross entry, fixed point target and stop

Price action:
    pattern_trades       trade a candlestick pattern mask with a stop at
                         the pattern extreme, an R multiple target and a
                         time stop
    ema_pullback_pattern trend filter from EMAs, entry trigger from a
                         bullish/bearish candle at the fast EMA
"""

import numpy as np

from . import indicators as ind


def _sides(long_entry, long_exit, short_entry, short_exit, side):
    sig = {}
    if side in ("long_only", "long_short"):
        sig.update(long_entry=long_entry, long_exit=long_exit)
    if side in ("short_only", "long_short"):
        sig.update(short_entry=short_entry, short_exit=short_exit)
    return sig


def _ready(n, warmup):
    return np.arange(n) >= warmup


def _event(state):
    prev = np.concatenate([[False], state[:-1]])
    return state & ~prev


def ema_cross(df, fast, slow, side="long_only"):
    c = df["close"]
    f, s = ind.ema(c, fast).to_numpy(), ind.ema(c, slow).to_numpy()
    ready = _ready(len(df), slow)
    above, below = (f > s) & ready, (f < s) & ready
    return _sides(above, below, below, above, side)


def ema_cross_filtered(df, fast, slow, side="long_only", trend_ema=None, adx_min=None,
                       atr_stop=None, atr_target=None, atr_trail=None, atr_n=14):
    c = df["close"]
    f, s = ind.ema(c, fast).to_numpy(), ind.ema(c, slow).to_numpy()
    warm = max(slow, trend_ema or 0, 2 * atr_n)
    ready = _ready(len(df), warm)
    above, below = (f > s) & ready, (f < s) & ready
    ok_long = np.ones(len(df), bool)
    ok_short = np.ones(len(df), bool)
    if trend_ema:
        t = ind.ema(c, trend_ema).to_numpy()
        ok_long &= c.to_numpy() > t
        ok_short &= c.to_numpy() < t
    if adx_min:
        a = ind.adx(df, 14)[0].to_numpy()
        ok_long &= a > adx_min
        ok_short &= a > adx_min
    sig = _sides(_event(above) & ok_long, below, _event(below) & ok_short, above, side)
    a = ind.atr(df, atr_n).to_numpy()
    if atr_stop:
        sig["stop_dist"] = atr_stop * a
    if atr_target:
        sig["target_dist"] = atr_target * a
    if atr_trail:
        sig["trail_dist"] = atr_trail * a
    return sig


def triple_ema(df, fast, mid, slow, side="long_only"):
    c = df["close"]
    f, m, s = (ind.ema(c, n).to_numpy() for n in (fast, mid, slow))
    ready = _ready(len(df), slow)
    bull = (f > m) & (m > s) & ready
    bear = (f < m) & (m < s) & ready
    return _sides(bull, (f < m) & ready, bear, (f > m) & ready, side)


def macd_cross(df, fast=12, slow=26, signal=9, side="long_only"):
    line, sig_line, _ = ind.macd(df["close"], fast, slow, signal)
    line, sig_line = line.to_numpy(), sig_line.to_numpy()
    ready = _ready(len(df), slow + signal)
    above, below = (line > sig_line) & ready, (line < sig_line) & ready
    return _sides(above, below, below, above, side)


def price_vs_ema(df, n, side="long_only"):
    c = df["close"].to_numpy()
    e = ind.ema(df["close"], n).to_numpy()
    ready = _ready(len(df), n)
    above, below = (c > e) & ready, (c < e) & ready
    return _sides(above, below, below, above, side)


def fixed_point_scalper(df, fast=9, slow=21, target_pts=8.0, stop_pts=5.0, max_bars=5):
    """
    Long on a bullish cross, short on a bearish cross, out at a fixed
    index point target or stop or after max_bars. 8/5 index points is
    roughly the 4/2.5 option premium points of the original idea at an
    ATM delta of about 0.5.
    """
    c = df["close"]
    f, s = ind.ema(c, fast).to_numpy(), ind.ema(c, slow).to_numpy()
    ready = _ready(len(df), slow)
    up, dn = _event((f > s) & ready), _event((f < s) & ready)
    n = len(df)
    return {"long_entry": up, "short_entry": dn, "stop_dist": np.full(n, stop_pts),
            "target_dist": np.full(n, target_pts), "max_bars": max_bars}


def with_session(sig, index, first_entry=None, last_entry="15:00", flat_from="15:15"):
    """
    Restrict a signal dict to intraday trading: no entries before
    first_entry or from last_entry on, forced exit at the first bar
    stamped at or after flat_from, and always flat on a day's last bar.
    Times compare against bar end stamps.
    """
    t = index.hour * 100 + index.minute
    hhmm = lambda s: int(s.replace(":", ""))
    day = index.normalize().to_numpy()
    last_of_day = np.append(day[1:] != day[:-1], True)
    allow = t < hhmm(last_entry)
    if first_entry:
        allow &= t >= hhmm(first_entry)
    flat = (t >= hhmm(flat_from)) | last_of_day
    out = dict(sig)
    out["allow_entry"] = np.asarray(allow) & np.asarray(sig.get("allow_entry", True))
    out["flat_at_close"] = np.asarray(flat)
    return out


def pattern_trades(df, mask, direction, hold=10, rr=2.0, stop="pattern", atr_n=14, atr_mult=1.0):
    """
    Enter at the next open after the pattern bar. Stop goes beyond the
    pattern bar's extreme (its low for bullish patterns, high for bearish)
    plus a small ATR buffer; the target is rr times that risk. Positions
    left open after `hold` bars exit at the close.

    stop="none" drops the stop and target and simply holds for `hold`
    bars, which is the pure event study version of the same trade.
    """
    mask = np.asarray(mask, bool)
    n = len(df)
    sig = {"max_bars": hold}
    if direction == 1:
        sig["long_entry"] = mask
    else:
        sig["short_entry"] = mask
    if stop == "pattern":
        a = ind.atr(df, atr_n).to_numpy()
        c = df["close"].to_numpy()
        extreme = df["low"].to_numpy() if direction == 1 else df["high"].to_numpy()
        # Distance from the signal close; the engine applies it to the
        # actual next-open fill, which keeps the risk unit fixed.
        risk = np.abs(c - extreme) + 0.1 * atr_mult * a
        risk = np.where(risk > 0, risk, a)
        sig["stop_dist"] = risk
        sig["target_dist"] = rr * risk if rr else np.zeros(n)
    return sig


def ema_pullback_pattern(df, pattern_mask, direction=1, fast=20, slow=50, hold=20, rr=2.0,
                         touch_atr=0.5):
    """
    Trend from EMAs, timing from candles: in an uptrend (fast EMA above
    slow EMA and close above slow EMA) take a bullish pattern whose bar
    traded within touch_atr ATRs of the fast EMA, i.e. a pullback to the
    moving average. Mirror rules for downtrends.
    """
    c = df["close"].to_numpy()
    f = ind.ema(df["close"], fast).to_numpy()
    s = ind.ema(df["close"], slow).to_numpy()
    a = ind.atr(df, 14).to_numpy()
    ready = _ready(len(df), slow)
    if direction == 1:
        trend = (f > s) & (c > s)
        touch = df["low"].to_numpy() <= f + touch_atr * a
    else:
        trend = (f < s) & (c < s)
        touch = df["high"].to_numpy() >= f - touch_atr * a
    mask = np.asarray(pattern_mask, bool) & trend & touch & ready
    return pattern_trades(df, mask, direction, hold=hold, rr=rr), mask
