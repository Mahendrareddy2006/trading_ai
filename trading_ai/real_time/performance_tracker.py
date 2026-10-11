import os
import json
import time
from datetime import datetime

# =====================================================
# FILE LOCATION
# =====================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "performance_state.json")

# =====================================================
# DEFAULT STRUCTURE
# =====================================================
def default_state():
    return {
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "total_pnl": 0,
        "daily": {}
    }

# =====================================================
# LOAD STATE
# =====================================================
def load_performance():
    if not os.path.exists(STATE_FILE):
        return default_state()

    with open(STATE_FILE, "r") as f:
        return json.load(f)

# =====================================================
# SAVE STATE
# =====================================================
def save_performance(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =====================================================
# RECORD TRADE RESULT
# =====================================================
def record_trade_result(pnl):

    data = load_performance()

    data["total_trades"] += 1
    data["total_pnl"] += pnl

    if pnl > 0:
        data["wins"] += 1
    else:
        data["losses"] += 1

    # ===== DAILY TRACKING =====
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if today not in data["daily"]:
        data["daily"][today] = {
            "trades": 0,
            "pnl": 0
        }

    data["daily"][today]["trades"] += 1
    data["daily"][today]["pnl"] += pnl

    save_performance(data)

# =====================================================
# CALCULATE STATS
# =====================================================
def get_statistics():

    data = load_performance()

    total = data["total_trades"]
    wins = data["wins"]
    losses = data["losses"]
    pnl = data["total_pnl"]

    win_rate = (wins / total * 100) if total > 0 else 0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(pnl, 2)
    }