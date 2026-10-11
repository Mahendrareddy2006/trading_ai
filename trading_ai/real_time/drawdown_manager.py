import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DRAWDOWN_FILE = os.path.join(BASE_DIR, "drawdown_state.json")

MAX_DRAWDOWN_PERCENT = 0.10  # 10%


def load_state():
    if not os.path.exists(DRAWDOWN_FILE):
        return {}

    with open(DRAWDOWN_FILE, "r") as f:
        return json.load(f)


def save_state(data):
    with open(DRAWDOWN_FILE, "w") as f:
        json.dump(data, f)


def initialize_drawdown(current_balance):
    state = load_state()

    if "peak_balance" not in state:
        state = {
            "peak_balance": current_balance,
            "trading_enabled": True
        }
        save_state(state)

    return state


def update_drawdown(current_balance):
    state = initialize_drawdown(current_balance)

    peak = state["peak_balance"]

    # Update peak if new high
    if current_balance > peak:
        state["peak_balance"] = current_balance
        save_state(state)
        return True

    # Calculate drawdown
    drawdown = (peak - current_balance) / peak

    if drawdown >= MAX_DRAWDOWN_PERCENT:
        state["trading_enabled"] = False
        save_state(state)
        return False

    return state.get("trading_enabled", True)


def can_trade_by_drawdown(current_balance):
    state = initialize_drawdown(current_balance)

    if not state.get("trading_enabled", True):
        return False

    return update_drawdown(current_balance)


def reset_drawdown():
    if os.path.exists(DRAWDOWN_FILE):
        os.remove(DRAWDOWN_FILE)