import time
from trading_ai.real_time.logger import log_info, log_error, log_trade

# ==========================================
# GET LAST CLOSED TRADE DATA
# ==========================================

def get_recent_income(client, symbol, start_time):

    try:
        income = client.futures_income_history(
            symbol=symbol,
            startTime=int(start_time * 1000)
        )

        realized_pnl = 0
        commission = 0
        funding = 0

        for record in income:
            income_type = record["incomeType"]
            amount = float(record["income"])

            if income_type == "REALIZED_PNL":
                realized_pnl += amount

            elif income_type == "COMMISSION":
                commission += amount

            elif income_type == "FUNDING_FEE":
                funding += amount

        return realized_pnl, commission, funding

    except Exception as e:
        log_error(f"Income fetch error: {e}")
        return 0, 0, 0


# ==========================================
# DETECT CLOSED POSITION
# ==========================================

def detect_trade_close(client, symbol, entry_timestamp):

    try:
        positions = client.futures_position_information(symbol=symbol)

        for pos in positions:
            if float(pos["positionAmt"]) == 0:

                # Position closed
                realized_pnl, commission, funding = get_recent_income(
                    client,
                    symbol,
                    entry_timestamp
                )

                net_pnl = realized_pnl + commission + funding

                result = "WIN" if net_pnl > 0 else "LOSS"

                log_info(f"Trade closed: {result}")
                log_trade(
                    f"CLOSED | Result: {result} | "
                    f"Realized: {realized_pnl} | "
                    f"Fees: {commission} | "
                    f"Funding: {funding} | "
                    f"Net: {net_pnl}"
                )

                return {
                    "result": result,
                    "realized": realized_pnl,
                    "commission": commission,
                    "funding": funding,
                    "net_pnl": net_pnl
                }

    except Exception as e:
        log_error(f"Trade close detection error: {e}")

    return None