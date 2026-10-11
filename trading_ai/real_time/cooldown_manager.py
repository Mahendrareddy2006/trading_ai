import os
import json
import time

COOLDOWN_FILE = "cooldown_state.json"

COOLDOWN_MINUTES = 15  # configurable
BLOCK_SAME_DIRECTION = True

def save_state(data):
    with open(COOLDOWN_FILE, "w") as f:
        json.dump(data, f)

def load_state():
    if not os.path.exists(COOLDOWN_FILE):
        return {}
    with open(COOLDOWN_FILE, "r") as f:
        return json.load(f)

def start_cooldown(direction):
    state = {
        "cooldown_until": time.time() + (COOLDOWN_MINUTES * 60),
        "last_direction": direction
    }
    save_state(state)

def can_trade(direction):
    state = load_state()

    if not state:
        return True

    cooldown_until = state.get("cooldown_until", 0)
    last_direction = state.get("last_direction")

    # Time-based cooldown
    if time.time() < cooldown_until:
        return False

    # Optional same direction block
    if BLOCK_SAME_DIRECTION and direction == last_direction:
        return False

    return True

def clear_cooldown():
    if os.path.exists(COOLDOWN_FILE):
        os.remove(COOLDOWN_FILE)