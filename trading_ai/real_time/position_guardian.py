import time
from binance.enums import *
from trading_ai.real_time.logger import log_info, log_warning, log_error
from trading_ai.real_time.risk_management import calculate_sl_tp


# ==========================================================
# GET OPEN POSITION
# ==========================================================

def get_open_position_data(client, symbol):
    try:
        positions = client.futures_position_information(symbol=symbol)

        for pos in positions:
            qty = float(pos["positionAmt"])

            if qty != 0:
                return {
                    "direction": "LONG" if qty > 0 else "SHORT",
                    "quantity": abs(qty),
                    "entry_price": float(pos["entryPrice"])
                }

    except Exception as e:
        log_error(f"Position fetch error: {e}")

    return None


# ==========================================================
# VERIFY PROTECTIVE ORDERS
# ==========================================================

def check_protective_orders(client, symbol):
    try:
        orders = client.futures_get_open_orders(symbol=symbol)

        has_sl = False
        has_tp = False

        for order in orders:
            if order["type"] == "STOP_MARKET":
                has_sl = True
            if order["type"] == "TAKE_PROFIT_MARKET":
                has_tp = True

        return has_sl, has_tp

    except Exception as e:
        log_error(f"Protective order check error: {e}")
        return False, False


# ==========================================================
# CANCEL ALL OPEN ORDERS
# ==========================================================

def cleanup_orders(client, symbol):
    try:
        client.futures_cancel_all_open_orders(symbol=symbol)
        log_warning("Orphan orders cleaned.")
    except Exception as e:
        log_error(f"Order cleanup failed: {e}")


# ==========================================================
# REBUILD PROTECTIVE ORDERS
# ==========================================================

def rebuild_protective_orders(client, symbol, position):

    direction = position["direction"]
    entry_price = position["entry_price"]
    quantity = position["quantity"]

    sl, tp = calculate_sl_tp(direction, entry_price)

    try:
        # Stop Loss
        client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL if direction == "LONG" else SIDE_BUY,
            type=FUTURE_ORDER_TYPE_STOP_MARKET,
            stopPrice=round(sl, 2),
            closePosition=True
        )

        # Take Profit
        client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL if direction == "LONG" else SIDE_BUY,
            type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
            stopPrice=round(tp, 2),
            closePosition=True
        )

        log_warning("Protective orders rebuilt successfully.")

    except Exception as e:
        log_error(f"Rebuild protective order error: {e}")


# ==========================================================
# FETCH LAST REALIZED PNL
# ==========================================================

def fetch_last_realized_pnl(client, symbol):
    try:
        income = client.futures_income_history(
            symbol=symbol,
            incomeType="REALIZED_PNL",
            limit=1
        )

        if income:
            pnl = float(income[0]["income"])
            log_info(f"Realized PnL: {pnl}")
            return pnl

    except Exception as e:
        log_error(f"PnL fetch error: {e}")

    return 0


# ==========================================================
# MONITOR POSITION (PRO VERSION)
# ==========================================================

def monitor_position(client, symbol):
    """
    Returns:
        None  -> No active position
        float -> Realized PnL when position closes
    """

    position = get_open_position_data(client, symbol)

    if not position:
        return None

    has_sl, has_tp = check_protective_orders(client, symbol)

    if not has_sl or not has_tp:
        log_warning("Protective orders missing. Rebuilding...")
        cleanup_orders(client, symbol)
        rebuild_protective_orders(client, symbol, position)

    # Wait until position closes
    while True:
        time.sleep(5)

        current_position = get_open_position_data(client, symbol)

        if not current_position:
            log_info("Position closed.")
            pnl = fetch_last_realized_pnl(client, symbol)
            return pnl