import sys
import os
import time
import requests
from binance.client import Client
from binance.enums import *

# ==========================================================
# ADD PROJECT ROOT TO PATH
# ==========================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
sys.path.append(PROJECT_ROOT)

# ==========================================================
# INTERNAL IMPORTS
# ==========================================================
from trading_ai.real_time.api_manager import safe_api_call
from trading_ai.real_time.logger import log_info, log_warning, log_error, log_trade
from trading_ai.real_time.config import BOT_TOKEN, CHAT_ID, API_KEY, API_SECRET
from trading_ai.real_time.risk_management import (
    calculate_sl_tp,
    calculate_position_size,
    can_trade,
    record_trade
)
from trading_ai.real_time.daily_risk_manager import can_trade_today, update_balance
from trading_ai.real_time.streak_manager import can_trade_by_streak
from trading_ai.real_time.drawdown_manager import can_trade_by_drawdown
from trading_ai.real_time.position_guardian import monitor_position
from trading_ai.real_time.trade_close_detector import detect_trade_close
from trading_ai.real_time.statistics_manager import record_trade_result
from trading_ai.real_time.cooldown_manager import (
    start_cooldown,
    can_trade as can_trade_cooldown,
    clear_cooldown
)
from trading_ai.real_time.strategy_factory import get_strategy

# ==========================================================
# CONFIG
# ==========================================================
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
LEVERAGE = 5
# Professional: Use edge (probability spread) instead of raw confidence
# Edge measures how much stronger the model favors one direction vs other
EDGE_THRESHOLD = 0.15  # Trade only if abs(UP_prob - DOWN_prob) > 15%

# Execution Engine: Limit orders for spread efficiency
LIMIT_ORDER_SPREAD_THRESHOLD = 0.001  # 0.1% spread threshold
LIMIT_ORDER_WAIT_SECONDS = 5  # Wait 5 seconds for limit fill before market
LIMIT_ORDER_SLIPPAGE = 0.0005  # Adjust limit by 0.05% for better fill chance

# Per-symbol runtime state
symbol_state = {
    symbol: {
        "entry_timestamp": None
    }
    for symbol in SYMBOLS
}

# ==========================================================
# VALIDATE API
# ==========================================================
if not API_KEY or not API_SECRET:
    log_error("API_KEY or API_SECRET missing.")
    sys.exit(1)

client = Client(API_KEY, API_SECRET)

# Set leverage safely for each symbol
for symbol in SYMBOLS:
    safe_api_call(
        client.futures_change_leverage,
        symbol=symbol,
        leverage=LEVERAGE
    )

# Initialize strategy
strategy = get_strategy("ema")

# ==========================================================
# TELEGRAM
# ==========================================================
def send_message(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text}
        )
    except Exception as e:
        log_warning(f"Telegram error: {e}")


def request_trade_permission(symbol, direction, price, edge, timeout=60):
    """Send Telegram approval request and wait for response.
    
    Waits up to *timeout* seconds (default 60 = 1 minute).
    User must reply APPROVE or REJECT.
    Returns True if approved, False if rejected or timeout.
    """
    send_message(
        f" TRADE APPROVAL REQUEST (expires in 1 minute)\n"
        f"Symbol: {symbol}\n"
        f"Direction: {direction}\n"
        f"Edge: {round(edge, 4)}\n"
        f"Entry Price: {price}\n\n"
        f"Reply with: APPROVE or REJECT"
    )

    last_update_id = None
    deadline = time.time() + timeout
    poll_interval = 1  # check every 1 second

    while time.time() < deadline:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={"offset": last_update_id, "timeout": 10}
            )
            data = resp.json()
            
            for upd in data.get("result", []):
                last_update_id = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue
                    
                chat = msg.get("chat", {}).get("id")
                if str(chat) != str(CHAT_ID):
                    continue
                    
                text = msg.get("text", "").strip().lower()
                if "approve" in text:
                    send_message(
                        f"✅ TRADE APPROVED!\n"
                        f"Symbol: {symbol}\n"
                        f"Direction: {direction}\n"
                        f"Edge: {round(edge, 4)}\n"
                        f"Entry: {price}\n\n"
                        f"Placing trade..."
                    )
                    return True
                elif "reject" in text:
                    send_message(
                        f"❌ TRADE REJECTED!\n"
                        f"Symbol: {symbol}\n"
                        f"Direction: {direction}\n"
                        f"Edge: {round(edge, 4)}\n"
                        f"Entry: {price}\n\n"
                        f"Trade cancelled."
                    )
                    return False
        except Exception as e:
            log_warning(f"Permission check error: {e}")
        
        time.sleep(poll_interval)

    # timeout
    send_message(
        f"TRADE EXPIRED!\n"
        f"Symbol: {symbol}\n"
        f"Direction: {direction}\n"
        f"Edge: {round(edge, 4)}\n"
        f"Entry: {price}\n\n"
        f"No response within 1 minute. Trade cancelled."
    )
    log_warning(f"Trade approval timeout for {symbol} {direction} @ {price}")
    return False


# ==========================================================
# EXECUTION ENGINE
# ==========================================================
def get_bid_ask_spread(client, symbol):
    """Get current bid-ask spread as percentage.
    
    Returns: (bid, ask, spread_pct)
    """
    try:
        ticker = client.get_symbol_info(symbol)
        
        # For futures, use mark price and estimate spread
        mark_price_data = safe_api_call(client.futures_mark_price, symbol=symbol)
        if mark_price_data:
            mark_price = float(mark_price_data["markPrice"])
            # Estimate spread (typically 0.01-0.1% on liquid pairs)
            estimated_spread = 0.0005  # Conservative 0.05% estimate for liquid futures
            bid = mark_price * (1 - estimated_spread / 2)
            ask = mark_price * (1 + estimated_spread / 2)
            spread_pct = (ask - bid) / bid
            return bid, ask, spread_pct
    except:
        pass
    
    return None, None, None


def select_execution_type(symbol, direction, entry_price):
    """Decide between LIMIT and MARKET order based on spread.
    
    Returns: ("LIMIT", limit_price) or ("MARKET", entry_price)
    
    Strategy:
    - If bid-ask spread < 0.1%: Use LIMIT (saves ~0.05% fees)
    - If bid-ask spread >= 0.1%: Use MARKET (ensure fill)
    """
    bid, ask, spread_pct = get_bid_ask_spread(client, symbol)
    
    if not spread_pct:
        return "MARKET", entry_price
    
    if spread_pct < LIMIT_ORDER_SPREAD_THRESHOLD:
        # Small spread: Use limit order with slight slippage tolerance
        if direction == "LONG":
            limit_price = entry_price * (1 + LIMIT_ORDER_SLIPPAGE)
        else:  # SHORT
            limit_price = entry_price * (1 - LIMIT_ORDER_SLIPPAGE)
        
        log_info(
            f"{symbol} LIMIT order selected (spread: {spread_pct*100:.3f}%, "
            f"limit_price: {limit_price})"
        )
        return "LIMIT", limit_price
    else:
        # Large spread: Use market order to ensure fill
        log_info(
            f"{symbol} MARKET order selected (spread: {spread_pct*100:.3f}%)"
        )
        return "MARKET", entry_price


def place_order_with_strategy(client, symbol, side, quantity, order_type, 
                             limit_price=None, wait_seconds=None):
    """Execute order with limit/market strategy.
    
    If LIMIT: Wait *wait_seconds* for fill, then fallback to market if not filled.
    """
    
    if order_type == "LIMIT":
        # Place limit order
        order_resp = safe_api_call(
            client.futures_create_order,
            symbol=symbol,
            side=side,
            type=FUTURE_ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=quantity,
            price=round(limit_price, 2)
        )
        
        if order_resp:
            order_id = order_resp.get("orderId")
            log_info(f"{symbol} LIMIT order placed: {order_id}")
            
            # Wait for fill
            if wait_seconds:
                deadline = time.time() + wait_seconds
                while time.time() < deadline:
                    order_status = safe_api_call(
                        client.futures_get_order,
                        symbol=symbol,
                        orderId=order_id
                    )
                    
                    if order_status and order_status.get("status") == "FILLED":
                        log_info(f"{symbol} LIMIT order FILLED: {order_id}")
                        return order_resp
                    
                    time.sleep(0.5)
                
                # Not filled, cancel and use market
                log_warning(
                    f"{symbol} LIMIT order not filled in {wait_seconds}s, "
                    "cancelling and using MARKET"
                )
                safe_api_call(
                    client.futures_cancel_order,
                    symbol=symbol,
                    orderId=order_id
                )
        
        # Fallback to market
        return place_order_with_strategy(
            client, symbol, side, quantity, "MARKET", wait_seconds=None
        )
    
    else:  # MARKET
        order_resp = safe_api_call(
            client.futures_create_order,
            symbol=symbol,
            side=side,
            type=FUTURE_ORDER_TYPE_MARKET,
            quantity=quantity
        )
        
        if order_resp:
            log_info(f"{symbol} MARKET order executed")
        
        return order_resp


# ==========================================================
# ACCOUNT
# ==========================================================
def get_balance():
    balance_info = safe_api_call(client.futures_account_balance)
    if not balance_info:
        return 0

    for asset in balance_info:
        if asset["asset"] == "USDT":
            return float(asset["balance"])

    return 0


def has_open_position(symbol):
    positions = safe_api_call(
        client.futures_position_information,
        symbol=symbol
    )

    if not positions:
        return False

    for pos in positions:
        if float(pos["positionAmt"]) != 0:
            return True

    return False

# ==========================================================
# TRADE EXECUTION
# ==========================================================
def place_trade(symbol, direction, price, edge):
    state = symbol_state[symbol]
    balance = get_balance()

    # ===== ASK FOR PERMISSION =====
    if not request_trade_permission(symbol, direction, price, edge, timeout=60):
        log_info(f"Trade {symbol} {direction} @ {price} rejected or expired.")
        return

    # ===== RISK STACK =====
    if not can_trade_today(balance):
        return

    if not can_trade_by_streak():
        return

    if not can_trade_by_drawdown(balance):
        return

    if not can_trade(balance):
        return

    if not can_trade_cooldown(direction):
        return

    quantity = calculate_position_size(balance, LEVERAGE, price)

    if quantity <= 0:
        return

    sl, tp = calculate_sl_tp(direction, price)
    side = SIDE_BUY if direction == "LONG" else SIDE_SELL

    # ===== EXECUTION ENGINE: SELECT LIMIT vs MARKET =====
    order_type, execution_price = select_execution_type(symbol, direction, price)
    
    if order_type == "LIMIT":
        # Attempt limit fill with market fallback
        place_order_with_strategy(
            client, symbol, side, quantity, 
            order_type="LIMIT",
            limit_price=execution_price, 
            wait_seconds=LIMIT_ORDER_WAIT_SECONDS
        )
    else:
        # Direct market order
        place_order_with_strategy(
            client, symbol, side, quantity, 
            order_type="MARKET",
            wait_seconds=None
        )

    state["entry_timestamp"] = time.time()

    # ===== STOP LOSS =====
    safe_api_call(
        client.futures_create_order,
        symbol=symbol,
        side=SIDE_SELL if direction == "LONG" else SIDE_BUY,
        type=FUTURE_ORDER_TYPE_STOP_MARKET,
        stopPrice=round(sl, 2),
        closePosition=True
    )

    # ===== TAKE PROFIT =====
    safe_api_call(
        client.futures_create_order,
        symbol=symbol,
        side=SIDE_SELL if direction == "LONG" else SIDE_BUY,
        type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
        stopPrice=round(tp, 2),
        closePosition=True
    )

    log_info(f"{symbol} Trade executed: {direction} ({order_type})")
    log_trade(f"{symbol} | {direction} | Entry: {price} | Qty: {quantity} | Type: {order_type}")

    record_trade()
    update_balance(balance)

    send_message(
        f" {symbol} Trade Executed ({order_type})\n"
        f"Direction: {direction}\n"
        f"Entry: {round(price,2)}\n"
        f"Qty: {quantity}"
    )

# ==========================================================
# MAIN LOOP
# ==========================================================
def run_bot():
    log_info("Multi-Symbol Futures Bot Started")
    print("Multi-Symbol Bot Running")

    while True:
        print("Loop started")
        try:
            for symbol in SYMBOLS:
                state = symbol_state[symbol]

                # ===== CLOSE DETECTION =====
                if state["entry_timestamp"]:
                    closed_trade = detect_trade_close(
                        client,
                        symbol,
                        state["entry_timestamp"]
                    )
                    print("Signals checked successfully")

                    if closed_trade:
                        pnl = closed_trade["net_pnl"]
                        record_trade_result(pnl)

                        if pnl < 0:
                            start_cooldown(closed_trade["direction"])
                        else:
                            clear_cooldown()

                        send_message(
                            f" {symbol} Trade Closed\n"
                            f"Result: {closed_trade['result']}\n"
                            f"Net PnL: ${round(pnl,2)}"
                        )

                        state["entry_timestamp"] = None
                        continue

                # ===== POSITION GUARDIAN =====
                if monitor_position(client, symbol):
                    continue

                if has_open_position(symbol):
                    continue

                # ===== STRATEGY =====
                signal, price, edge = strategy.generate_signal(client, symbol)

                if signal and edge >= EDGE_THRESHOLD:
                    place_trade(symbol, signal, price, edge)

            time.sleep(5)

        except Exception as e:
            log_error(f"Main loop error: {e}")
            time.sleep(5)

# ==========================================================
# START
# ==========================================================
if __name__ == "__main__":
    run_bot()
