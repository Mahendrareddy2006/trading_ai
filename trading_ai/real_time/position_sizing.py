from binance.client import Client
from trading_ai.real_time.config import RISK_PERCENT_PER_TRADE, API_KEY, API_SECRET

import os
client = Client(os.getenv("BINANCE_API_KEY", ""), os.getenv("BINANCE_API_SECRET", ""))


def get_account_balance():
    account = client.get_account()
    balances = account["balances"]

    for asset in balances:
        if asset["asset"] == "USDT":
            return float(asset["free"])

    return 0


def calculate_position_size(entry, sl):

    balance = get_account_balance()

    risk_amount = balance * RISK_PERCENT_PER_TRADE
    sl_distance = abs(entry - sl)

    if sl_distance == 0:
        return 0

    position_size = risk_amount / sl_distance

    return round(position_size, 6)