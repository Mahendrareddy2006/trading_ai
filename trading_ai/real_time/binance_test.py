from binance.client import Client
import time
import sys

import os

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")

client = Client(API_KEY, API_SECRET)

previous_price = None
high_level = 66000   # Example breakout resistance
low_level = 64000    # Example breakout support

while True:
    try:
        data = client.get_symbol_ticker(symbol="BTCUSDT")
        current_price = float(data["price"])

        if previous_price is None:
            previous_price = current_price

        # Calculate price difference
        difference = current_price - previous_price
        percent_change = (difference / previous_price) * 100

        # Determine direction
        if difference > 0:
            arrow = "📈"
            color = "\033[92m"   # Green
        elif difference < 0:
            arrow = "📉"
            color = "\033[91m"   # Red
        else:
            arrow = "➡"
            color = "\033[0m"    # Default

        # Breakout detection
        breakout_message = ""
        if current_price > high_level:
            breakout_message = " 🚀 BREAKOUT ABOVE RESISTANCE!"
        elif current_price < low_level:
            breakout_message = " 💥 BREAKDOWN BELOW SUPPORT!"

        # Print clean updating line
        sys.stdout.write(
            f"\r{color}BTC: {current_price:.2f} {arrow} "
            f"{percent_change:.4f}%{breakout_message}\033[0m"
        )
        sys.stdout.flush()

        previous_price = current_price
        time.sleep(5)

    except Exception as e:
        print("\nError:", e)
        time.sleep(5)