"""
Volatility regime and event day gate. The research report recommends
applying this as a global filter on top of every strategy in this repo,
not just Strategy 7.

It needs a real IV time series (India VIX, or your own Black-76 IV from
option mid prices) and an events calendar, both of which are broker or
vendor specific. Rather than fake that data here, this is left as a
documented interface: wire it to your own feed before relying on it.
"""


def passes_gate(iv_rank, is_event_day, iv_rank_ceiling=0.75):
    """
    iv_rank: current ATM IV's percentile rank over roughly the last year (0-1).
    is_event_day: True on the day before or of RBI policy, Budget, major
    CPI or Fed decisions, when IV crush risk is highest.

    Returns False (skip trading) when IV is rich or it is an event day.
    """
    if is_event_day:
        return False
    return iv_rank <= iv_rank_ceiling
