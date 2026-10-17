"""
Rule based candlestick pattern detection.

Every pattern is a pure function of the current and previous bars, so a
pattern detected at bar t is known at t's close and can be traded from
t+1's open. Size comparisons ("long body", "small body") use the average
body or range of the 10 bars before the pattern, as TA-Lib does, so the
pattern bars themselves never set their own yardstick.

Definitions follow the common textbook forms (Nison, Bulkowski, TA-Lib).
Classic star and piercing patterns require gaps that are rare on daily
NSE stocks and Indian indices, so those rules accept a touch (no body
overlap) instead of a strict gap. Trend context is deliberately NOT part
of the shape rules here; the study applies it separately so its effect
can be measured on its own.
"""

import numpy as np
import pandas as pd


def _shift(a, k):
    out = np.empty_like(a)
    out[:k] = np.nan
    out[k:] = a[:-k]
    return out


def _trailing_mean(a, n=10):
    """Mean of the n values before each bar (excludes the bar itself)."""
    return pd.Series(a).rolling(n).mean().shift(1).to_numpy()


def detect(df):
    """
    Returns a DataFrame of boolean columns, one per pattern, plus a
    PATTERNS dict saying which direction each pattern predicts.
    """
    o = df["open"].to_numpy(np.float64)
    h = df["high"].to_numpy(np.float64)
    l = df["low"].to_numpy(np.float64)
    c = df["close"].to_numpy(np.float64)

    body = np.abs(c - o)
    rng = h - l
    top = np.maximum(o, c)
    bot = np.minimum(o, c)
    upper = h - top
    lower = bot - l
    bull = c > o
    bear = c < o
    avg_body = _trailing_mean(body)
    avg_rng = _trailing_mean(rng)
    valid = (rng > 0) & np.isfinite(avg_body) & (avg_body > 0)

    o1, h1, l1, c1 = _shift(o, 1), _shift(h, 1), _shift(l, 1), _shift(c, 1)
    o2, c2 = _shift(o, 2), _shift(c, 2)
    body1, body2 = _shift(body, 1), _shift(body, 2)
    top1, bot1 = np.maximum(o1, c1), np.minimum(o1, c1)
    bull1, bear1 = c1 > o1, c1 < o1
    bull2, bear2 = c2 > o2, c2 < o2
    avg_body1 = _shift(avg_body, 1)
    avg_body2 = _shift(avg_body, 2)
    long_body1 = body1 > avg_body1
    long_body2 = body2 > avg_body2

    with np.errstate(invalid="ignore"):
        small_body = body <= 0.35 * rng
        p = {}

        # Two bar reversals
        p["bullish_engulfing"] = bear1 & bull & (o <= c1) & (c >= o1) & (body > body1)
        p["bearish_engulfing"] = bull1 & bear & (o >= c1) & (c <= o1) & (body > body1)
        p["piercing_line"] = (bear1 & long_body1 & bull & (o < c1) & (c > (o1 + c1) / 2) & (c < o1))
        p["dark_cloud_cover"] = (bull1 & long_body1 & bear & (o > c1) & (c < (o1 + c1) / 2) & (c > o1))
        p["bullish_harami"] = bear1 & long_body1 & (body < 0.5 * body1) & (top <= o1) & (bot >= c1)
        p["bearish_harami"] = bull1 & long_body1 & (body < 0.5 * body1) & (top <= c1) & (bot >= o1)

        # One bar shapes. Hammer and hanging man share a shape and differ
        # only by context, so the shape is reported once per direction.
        hammer_shape = small_body & (lower >= 2 * body) & (upper <= 0.1 * rng) & (body > 0)
        star_shape = small_body & (upper >= 2 * body) & (lower <= 0.1 * rng) & (body > 0)
        p["hammer"] = hammer_shape
        p["hanging_man"] = hammer_shape
        p["inverted_hammer"] = star_shape
        p["shooting_star"] = star_shape
        # Price action pin bars: long wick rejecting a new low/high
        p["bullish_pin_bar"] = (lower >= 2 / 3 * rng) & (c >= l + 2 / 3 * rng) & (l < l1)
        p["bearish_pin_bar"] = (upper >= 2 / 3 * rng) & (c <= l + 1 / 3 * rng) & (h > h1)
        doji = body <= 0.1 * rng
        p["dragonfly_doji"] = doji & (upper <= 0.1 * rng) & (lower >= 0.6 * rng)
        p["gravestone_doji"] = doji & (lower <= 0.1 * rng) & (upper >= 0.6 * rng)
        p["bullish_marubozu"] = bull & (body >= 0.9 * rng) & (rng > avg_rng)
        p["bearish_marubozu"] = bear & (body >= 0.9 * rng) & (rng > avg_rng)

        # Three bar patterns
        star_small1 = body1 <= 0.5 * body2
        p["morning_star"] = (bear2 & long_body2 & star_small1 & (top1 <= c2) & bull & (c >= (o2 + c2) / 2))
        p["evening_star"] = (bull2 & long_body2 & star_small1 & (bot1 >= c2) & bear & (c <= (o2 + c2) / 2))
        o_in_body = (o > o1) & (o < c1)
        o_in_body1 = (o1 > o2) & (o1 < c2)
        p["three_white_soldiers"] = (bull & bull1 & bull2 & (c > c1) & (c1 > c2) & o_in_body & o_in_body1
                                     & (body > avg_body) & (upper < 0.3 * body))
        o_in_body_dn = (o < o1) & (o > c1)
        o_in_body1_dn = (o1 < o2) & (o1 > c2)
        p["three_black_crows"] = (bear & bear1 & bear2 & (c < c1) & (c1 < c2) & o_in_body_dn & o_in_body1_dn
                                  & (body > avg_body) & (lower < 0.3 * body))

        # Inside bar breakout: bar t-1 sits inside bar t-2, bar t closes
        # beyond the inside bar's range
        h2, l2 = _shift(h, 2), _shift(l, 2)
        inside1 = (h1 < h2) & (l1 > l2)
        p["inside_bar_breakout_up"] = inside1 & (c > h1)
        p["inside_bar_breakout_down"] = inside1 & (c < l1)

    out = pd.DataFrame({k: np.nan_to_num(v.astype(float)).astype(bool) & valid for k, v in p.items()},
                       index=df.index)
    return out


# Direction each pattern predicts, and whether it is a reversal pattern
# (meaningful after a move against it) or a continuation pattern.
PATTERNS = {
    "bullish_engulfing": (1, "reversal"),
    "bearish_engulfing": (-1, "reversal"),
    "piercing_line": (1, "reversal"),
    "dark_cloud_cover": (-1, "reversal"),
    "bullish_harami": (1, "reversal"),
    "bearish_harami": (-1, "reversal"),
    "hammer": (1, "reversal"),
    "hanging_man": (-1, "reversal"),
    "inverted_hammer": (1, "reversal"),
    "shooting_star": (-1, "reversal"),
    "bullish_pin_bar": (1, "reversal"),
    "bearish_pin_bar": (-1, "reversal"),
    "dragonfly_doji": (1, "reversal"),
    "gravestone_doji": (-1, "reversal"),
    "morning_star": (1, "reversal"),
    "evening_star": (-1, "reversal"),
    "three_white_soldiers": (1, "continuation"),
    "three_black_crows": (-1, "continuation"),
    "bullish_marubozu": (1, "continuation"),
    "bearish_marubozu": (-1, "continuation"),
    "inside_bar_breakout_up": (1, "continuation"),
    "inside_bar_breakout_down": (-1, "continuation"),
}


def trend_context(df, lookback=5, ema_span=20):
    """
    Prior trend at each bar, used to put reversal patterns in context:
    +1 when the last `lookback` bars rose and close is above its EMA,
    -1 when they fell and close is below it, 0 otherwise.
    """
    c = df["close"]
    e = c.ewm(span=ema_span, adjust=False).mean()
    move = c - c.shift(lookback)
    ctx = np.where((move > 0) & (c > e), 1, np.where((move < 0) & (c < e), -1, 0))
    return pd.Series(ctx, index=df.index)


def in_context(name, ctx):
    """
    Reversal patterns count only against the prior trend (a hammer after
    a decline, a hanging man after a rise). Continuation patterns count
    only with it.
    """
    direction, kind = PATTERNS[name]
    if kind == "reversal":
        return ctx == -direction
    return ctx == direction
