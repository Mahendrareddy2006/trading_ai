import time
from trading_ai.real_time.logger import log_info, log_error
from trading_ai.real_time.api_manager import safe_api_call


def detect_trade_close(client, symbol, entry_timestamp):
    """
    Detects if position opened after entry_timestamp has been closed.
    
    Returns:
        None if trade still open
        dict {
            "net_pnl": float,
            "result": "WIN" or "LOSS",
            "direction": "LONG" or "SHORT"
        }
    """

    # Check if position still exists
    positions = safe_api_call(
        client.futures_position_information,
        symbol=symbol
    )

    if not positions:
        return None

    for pos in positions:
        qty = float(pos["positionAmt"])

        # If position still open → do nothing
        if qty != 0:
            return None

    # Position closed → fetch realized PnL
    income = safe_api_call(
        client.futures_income_history,
        symbol=symbol,
        incomeType="REALIZED_PNL",
        limit=5
    )

    if not income:
        return None

    # Find income after entry_timestamp
    for record in income:
        income_time = record.get("time", 0) / 1000  # convert ms to seconds

        if income_time >= entry_timestamp:
            pnl = float(record["income"])

            result = "WIN" if pnl > 0 else "LOSS"

            log_info(f"Trade closed detected. PnL: {pnl}")

            return {
                "net_pnl": pnl,
                "result": result,
                "direction": "LONG" if pnl > 0 else "SHORT"
            }

    return None