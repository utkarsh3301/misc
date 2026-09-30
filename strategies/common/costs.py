"""
NSE options transaction cost model, 2026 rates.

Rates are sourced from the strategy research report (brokerage, STT,
exchange transaction charges, SEBI fee, stamp duty, GST), applicable to a
discount broker such as Zerodha. Validated against the report's worked
examples: a 1-lot Nifty (lot=65) round trip from 100 to 104 premium costs
about 0.97 premium points. A 1-lot Bank Nifty (lot=30) round trip from
300 to 304 premium leaves about 1.7 points after costs, before slippage.
"""

BROKERAGE_PER_ORDER = 20.0     # flat fee per executed order (buy or sell)
STT_RATE_SELL = 0.0015         # 0.15% of premium, sell side only
EXCHANGE_RATE = 0.0003503      # 0.03503% of premium turnover, both sides
SEBI_RATE = 10 / 1e7           # Rs 10 per crore turnover, both sides
STAMP_RATE_BUY = 0.00003       # 0.003% of premium turnover, buy side only
GST_RATE = 0.18                # on brokerage + exchange charges + SEBI fee

LOT_SIZE = {
    "NIFTY": 65,
    "BANKNIFTY": 30,
}


def round_trip_cost(entry_premium, exit_premium, lot_size, num_lots,
                     slippage_points_per_side=0.5):
    """
    Total round trip cost in rupees and in premium points for a long
    option bought at entry_premium and sold at exit_premium.

    entry_premium / exit_premium can be scalars or numpy arrays. All the
    formulas are linear in turnover, so this vectorises without changes.
    """
    units = lot_size * num_lots
    turnover_buy = entry_premium * units
    turnover_sell = exit_premium * units

    brokerage = 2 * BROKERAGE_PER_ORDER
    stt = STT_RATE_SELL * turnover_sell
    exch = EXCHANGE_RATE * (turnover_buy + turnover_sell)
    sebi = SEBI_RATE * (turnover_buy + turnover_sell)
    stamp = STAMP_RATE_BUY * turnover_buy
    gst = GST_RATE * (brokerage + exch + sebi)

    statutory_and_brokerage = brokerage + stt + exch + sebi + stamp + gst
    slippage_rupees = slippage_points_per_side * 2 * units

    total_rupees = statutory_and_brokerage + slippage_rupees
    total_points = total_rupees / units

    return {
        "brokerage": brokerage,
        "stt": stt,
        "exchange": exch,
        "sebi": sebi,
        "stamp": stamp,
        "gst": gst,
        "slippage_rupees": slippage_rupees,
        "total_cost_rupees": total_rupees,
        "total_cost_points": total_points,
    }


def breakeven_win_rate(target_points, stop_points, entry_premium, lot_size,
                        num_lots, slippage_points_per_side=0.5):
    """
    Win rate needed for zero expectancy given a fixed target/stop pair,
    after costs and slippage. Used to sanity check fixed point scalping
    setups such as the original Strategy 1 spec (4 point target).
    """
    win_cost = round_trip_cost(entry_premium, entry_premium + target_points,
                                lot_size, num_lots, slippage_points_per_side)
    loss_cost = round_trip_cost(entry_premium, entry_premium - stop_points,
                                 lot_size, num_lots, slippage_points_per_side)
    units = lot_size * num_lots
    net_win = target_points * units - win_cost["total_cost_rupees"]
    net_loss = stop_points * units + loss_cost["total_cost_rupees"]
    breakeven = net_loss / (net_win + net_loss)
    return breakeven, net_win, net_loss
