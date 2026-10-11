import os
import json
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DAILY_FILE = os.path.join(BASE_DIR, "daily_stats.json")

# 🔒 Max daily loss (2% example)
MAX_DAILY_LOSS_PERCENT = 0.02


def _today():
    return datetime.date.today().isoformat()


def load_daily_stats():
    if not os.path.exists(DAILY_FILE):
        return {}

    with open(DAILY_FILE, "r") as f:
        return json.load(f)


def save_daily_stats(data):
    with open(DAILY_FILE, "w") as f:
        json.dump(data, f)


def initialize_day(current_balance):
    stats = load_daily_stats()

    if stats.get("date") != _today():
        stats = {
            "date": _today(),
            "start_balance": current_balance,
            "current_balance": current_balance,
            "trading_enabled": True
        }
        save_daily_stats(stats)

    return stats


def update_balance(current_balance):
    stats = load_daily_stats()

    stats["current_balance"] = current_balance
    save_daily_stats(stats)


def can_trade_today(current_balance):
    stats = initialize_day(current_balance)

    if not stats.get("trading_enabled", True):
        return False

    start_balance = stats["start_balance"]

    loss = start_balance - current_balance
    loss_percent = loss / start_balance

    if loss_percent >= MAX_DAILY_LOSS_PERCENT:
        stats["trading_enabled"] = False
        save_daily_stats(stats)
        return False

    return True