"""
Bar by bar backtester.

Execution rules, chosen to avoid look-ahead and to err against the
strategy:

- Signals are read at a bar's close and filled at the next bar's open.
- Protective stops and targets are fixed at entry from the signal bar's
  distances and checked intrabar from the entry bar onward. A gap through
  the level fills at the open, not at the level.
- If a bar touches both the stop and the target, the stop is assumed to
  have filled first.
- A time stop of N bars exits at the close of the Nth bar held.
- flat_at_close forces an exit at that bar's close and blocks new orders
  from it (intraday sessions). allow_entry masks new entries only; exits
  and stops always work.
- Costs are a fraction of notional charged on every fill.
- Positions are always 1x notional, long (+1) or short (-1). Bar returns
  compound, so the equity curve is a fully invested account.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numba import njit

EXIT_REASONS = np.array(["signal", "stop", "target", "time", "session", "end"])


@njit(cache=True)
def _simulate(o, h, l, c, long_entry, long_exit, short_entry, short_exit,
              allow_entry, flat_at_close, stop_dist, target_dist, trail_dist,
              max_bars, cost):
    n = c.shape[0]
    ret = np.zeros(n)
    pos = np.zeros(n, np.int8)
    t_entry = np.empty(n, np.int64)
    t_exit = np.empty(n, np.int64)
    t_dir = np.empty(n, np.int8)
    t_entry_px = np.empty(n)
    t_exit_px = np.empty(n)
    t_reason = np.empty(n, np.int8)
    nt = 0

    cur = 0
    entry_px = 0.0
    entry_i = -1
    stop = np.nan
    target = np.nan
    pending = 0
    has_pending = False

    for i in range(n):
        mult = 1.0
        ref = c[i - 1] if i > 0 else o[i]

        # 1. orders decided at the previous close fill at this open
        if has_pending and pending != cur:
            if cur != 0:
                mult *= (1.0 + cur * (o[i] / ref - 1.0)) * (1.0 - cost)
                t_entry[nt] = entry_i
                t_exit[nt] = i
                t_dir[nt] = cur
                t_entry_px[nt] = entry_px
                t_exit_px[nt] = o[i]
                t_reason[nt] = 0
                nt += 1
                cur = 0
            if pending != 0:
                cur = pending
                entry_px = o[i]
                entry_i = i
                mult *= 1.0 - cost
                sd = stop_dist[i - 1]
                td = target_dist[i - 1]
                stop = entry_px - cur * sd if sd > 0 else np.nan
                target = entry_px + cur * td if td > 0 else np.nan
            ref = o[i]
        has_pending = False

        # 2. intrabar exits for an open position
        if cur != 0:
            pos[i] = cur
            fresh = i == entry_i
            exit_px = np.nan
            reason = -1
            if cur == 1:
                if stop == stop and l[i] <= stop:
                    exit_px = stop if fresh else min(o[i], stop)
                    reason = 1
                elif target == target and h[i] >= target:
                    exit_px = target if fresh else max(o[i], target)
                    reason = 2
            else:
                if stop == stop and h[i] >= stop:
                    exit_px = stop if fresh else max(o[i], stop)
                    reason = 1
                elif target == target and l[i] <= target:
                    exit_px = target if fresh else min(o[i], target)
                    reason = 2
            if reason < 0:
                if max_bars > 0 and i - entry_i + 1 >= max_bars:
                    exit_px = c[i]
                    reason = 3
                elif flat_at_close[i]:
                    exit_px = c[i]
                    reason = 4
                elif i == n - 1:
                    exit_px = c[i]
                    reason = 5
            if reason >= 0:
                mult *= (1.0 + cur * (exit_px / ref - 1.0)) * (1.0 - cost)
                t_entry[nt] = entry_i
                t_exit[nt] = i
                t_dir[nt] = cur
                t_entry_px[nt] = entry_px
                t_exit_px[nt] = exit_px
                t_reason[nt] = reason
                nt += 1
                cur = 0
            else:
                mult *= 1.0 + cur * (c[i] / ref - 1.0)
                td = trail_dist[i]
                if td > 0:
                    if cur == 1:
                        level = c[i] - td
                        if stop != stop or level > stop:
                            stop = level
                    else:
                        level = c[i] + td
                        if stop != stop or level < stop:
                            stop = level
        ret[i] = mult - 1.0

        # 3. signals at this close set the order for the next open
        if i < n - 1 and not flat_at_close[i]:
            can_enter = allow_entry[i]
            if cur == 1:
                if short_entry[i] and can_enter:
                    pending = -1
                    has_pending = True
                elif long_exit[i]:
                    pending = 0
                    has_pending = True
            elif cur == -1:
                if long_entry[i] and can_enter:
                    pending = 1
                    has_pending = True
                elif short_exit[i]:
                    pending = 0
                    has_pending = True
            elif can_enter:
                if long_entry[i]:
                    pending = 1
                    has_pending = True
                elif short_entry[i]:
                    pending = -1
                    has_pending = True

    return (ret, pos, t_entry[:nt], t_exit[:nt], t_dir[:nt], t_entry_px[:nt],
            t_exit_px[:nt], t_reason[:nt])


@dataclass
class Result:
    returns: pd.Series
    position: pd.Series
    trades: pd.DataFrame
    cost: float


def _bool(x, n, default=False):
    if x is None:
        return np.full(n, default)
    return np.asarray(x, dtype=np.bool_)


def _float(x, n):
    if x is None:
        return np.zeros(n)
    if np.isscalar(x):
        return np.full(n, float(x))
    return np.nan_to_num(np.asarray(x, dtype=np.float64), nan=0.0)


def run(df, signals, cost=0.0):
    """
    df: OHLC DataFrame. signals: dict with any of long_entry, long_exit,
    short_entry, short_exit, allow_entry, flat_at_close (bool arrays),
    stop_dist, target_dist, trail_dist (price distances, 0 = none) and
    max_bars (int, 0 = none). cost: fraction of notional per fill.
    """
    n = len(df)
    o = df["open"].to_numpy(np.float64)
    h = df["high"].to_numpy(np.float64)
    l = df["low"].to_numpy(np.float64)
    c = df["close"].to_numpy(np.float64)
    out = _simulate(
        o, h, l, c,
        _bool(signals.get("long_entry"), n), _bool(signals.get("long_exit"), n),
        _bool(signals.get("short_entry"), n), _bool(signals.get("short_exit"), n),
        _bool(signals.get("allow_entry"), n, default=True), _bool(signals.get("flat_at_close"), n),
        _float(signals.get("stop_dist"), n), _float(signals.get("target_dist"), n),
        _float(signals.get("trail_dist"), n), int(signals.get("max_bars", 0)), float(cost),
    )
    ret, pos, te, tx, td, tep, txp, tr = out
    gross = td * (txp / tep - 1.0)
    net = (1.0 + gross) * (1.0 - cost) ** 2 - 1.0
    trades = pd.DataFrame({
        "entry_time": df.index[te], "exit_time": df.index[tx],
        "entry_i": te, "exit_i": tx, "direction": td,
        "entry_price": tep, "exit_price": txp,
        "gross_ret": gross, "ret": net, "bars": tx - te + 1,
        "exit_reason": EXIT_REASONS[tr],
    })
    return Result(pd.Series(ret, index=df.index), pd.Series(pos, index=df.index), trades, cost)
