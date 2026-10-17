"""
Transaction cost assumptions, expressed as a cost per fill (one side) in
basis points of traded notional. The engine charges this on every entry
and every exit, so a round trip costs twice the number below.

NSE index futures, 2026 rates (STT on futures raised from 0.02% to 0.05%
of sell value from 1 April 2026, Budget 2026-27):

    STT 0.05% on the sell side            -> 2.50 bps per side (averaged)
    exchange charge 0.00173% per side      -> 0.17
    SEBI fee Rs 10 per crore               -> 0.01
    stamp duty 0.002% on the buy side      -> 0.10 (averaged)
    brokerage Rs 20/order on ~Rs 16 lakh   -> 0.12
    GST 18% on brokerage + exchange + SEBI -> 0.06
    slippage, about 1.25 Nifty points      -> 0.50
    total                                  ~ 3.5 bps per side, ~7 bps round trip

The same stack at the Oct 2024 - Mar 2026 STT rate (0.02%) is about
2.0 bps per side. Earlier years were cheaper still; using today's cost
for the whole history is deliberately conservative for anyone deciding
whether to trade these rules now.

NSE equity delivery (cash market swing trades, long only):

    STT 0.1% buy and 0.1% sell             -> 10.0 bps per side
    exchange 0.00297% + SEBI + GST         -> 0.4
    stamp duty 0.015% on the buy side      -> 0.75 (averaged)
    DP charge ~Rs 16 per sell              -> 0.5 (on a few lakh)
    slippage, large caps                   -> 3.0
    total                                  ~ 14.5 bps per side, ~29 bps round trip

Global markets (OANDA CFDs, Bitstamp BTC) use typical retail spread plus
slippage. Overnight CFD financing, dividends and interest on idle cash
are ignored for every market, so all returns are price returns.
"""

NSE_FUTURES_2026 = 3.5
NSE_FUTURES_2024 = 2.0
NSE_DELIVERY = 14.5
NSE_STOCK_FUTURES = 6.0   # futures stack plus wider single stock slippage

GLOBAL = {
    "SPX500_USD": 1.5,
    "NAS100_USD": 1.5,
    "EUR_USD": 1.0,
    "GBP_USD": 1.2,
    "XAU_USD": 2.0,
    "WTICO_USD": 3.0,
    "BTC_USD": 15.0,
}


def per_side(bps):
    """Convert basis points to the fraction the engine expects."""
    return bps / 1e4


def nse_futures_per_side_bps(stt_sell=0.0005, slippage_bps=0.5):
    """Rebuild the NSE futures figure above for another STT rate or slippage."""
    stt = stt_sell * 1e4 / 2
    exchange, sebi, stamp, brokerage = 0.173, 0.01, 0.1, 0.12
    gst = 0.18 * (brokerage + exchange + sebi)
    return stt + exchange + sebi + stamp + brokerage + gst + slippage_bps
