import os
import json
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STREAK_FILE = os.path.join(BASE_DIR, "streak_stats.json")

MAX_CONSECUTIVE_LOSSES = 3


def _today():
    return datetime.date.today().isoformat()


def load_streak():
    if not os.path.exists(STREAK_FILE):
        return {}

    with open(STREAK_FILE, "r") as f:
        return json.load(f)


def save_streak(data):
    with open(STREAK_FILE, "w") as f:
        json.dump(data, f)


def initialize_streak():
    stats = load_streak()

    if stats.get("date") != _today():
        stats = {
            "date": _today(),
            "consecutive_losses": 0,
            "trading_enabled": True
        }
        save_streak(stats)

    return stats


def record_trade_result(pnl):
    """
    pnl > 0  → win
    pnl < 0  → loss
    """

    stats = initialize_streak()

    if pnl > 0:
        stats["consecutive_losses"] = 0
    else:
        stats["consecutive_losses"] += 1

    if stats["consecutive_losses"] >= MAX_CONSECUTIVE_LOSSES:
        stats["trading_enabled"] = False

    save_streak(stats)


def can_trade_by_streak():
    stats = initialize_streak()
    return stats.get("trading_enabled", True)