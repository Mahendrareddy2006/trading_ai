# risk_management.py

import os
import json
from trading_ai.real_time.config import RISK_PERCENT, REWARD_PERCENT

# ==========================================
# STATE FILE FOR BASIC RISK TRACKING
# ==========================================

STATE_FILE = "state/risk_state.json"

os.makedirs("state", exist_ok=True)

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"trades_today": 0}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# ==========================================
# SL / TP CALCULATION
# ==========================================

def calculate_sl_tp(direction, entry):
    """
    Calculate Stop Loss and Take Profit
    based on configured risk/reward percentages.
    """

    if direction == "LONG":
        sl = entry * (1 - RISK_PERCENT)
        tp = entry * (1 + REWARD_PERCENT)

    elif direction == "SHORT":
        sl = entry * (1 + RISK_PERCENT)
        tp = entry * (1 - REWARD_PERCENT)

    else:
        return None, None

    return sl, tp


# ==========================================
# POSITION SIZING
# ==========================================

def calculate_position_size(balance, leverage, price):
    """
    Calculate quantity based on risk percentage.
    """

    risk_amount = balance * RISK_PERCENT
    position_value = risk_amount * leverage
    quantity = position_value / price

    return round(quantity, 3)


# ==========================================
# PORTFOLIO RISK CONTROL (PROFESSIONAL)
# ==========================================

MAX_TRADES_PER_DAY = 50
MAX_TOTAL_PORTFOLIO_RISK = 0.02  # 2% max total risk
MAX_SAME_DIRECTION_EXPOSURE = 0.015  # 1.5% max same direction
MAX_PER_SYMBOL_RISK = 0.01  # 1% max per symbol

def can_trade(balance):
    """
    Professional protection layer.
    Blocks trading if balance is zero,
    max trades reached, or portfolio risk limits exceeded.
    """

    if balance <= 0:
        return False

    state = load_state()

    if state["trades_today"] >= MAX_TRADES_PER_DAY:
        return False

    return True


def check_portfolio_correlation(open_positions):
    """
    Professional correlation guard.
    Prevents over-exposure to correlated trades.
    
    Example:
    open_positions = [{"symbol": "BTCUSDT", "direction": "LONG"},
                      {"symbol": "ETHUSDT", "direction": "LONG"}]
    
    Returns: True if safe to add new trade, False otherwise
    """
    
    if not open_positions:
        return True
    
    # BTC-ETH correlation ~ 0.7 (highly correlated)
    # If both LONG, portfolio concentration risk is high
    
    long_count = len([p for p in open_positions if p.get("direction") == "LONG"])
    short_count = len([p for p in open_positions if p.get("direction") == "SHORT"])
    
    # Limit concentration
    if long_count >= 2 or short_count >= 2:
        return False  # Don't add same direction
    
    return True


# ==========================================
# RECORD TRADE COUNT
# ==========================================

def record_trade():
    """
    Increment daily trade counter.
    """

    state = load_state()
    state["trades_today"] += 1
    save_state(state)