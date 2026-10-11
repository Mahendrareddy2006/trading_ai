from binance.client import Client
import pandas as pd
import os
from datetime import datetime

# 🔐 If only public data, no need API keys
client = Client()

DATA_FOLDER = "data"

# Coins and timeframes
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
INTERVALS = {

    "1h": Client.KLINE_INTERVAL_1HOUR,
    "4h": Client.KLINE_INTERVAL_4HOUR,
    "3m": Client.KLINE_INTERVAL_3MINUTE,
    "5m": Client.KLINE_INTERVAL_5MINUTE
}


# Number of days of history
LOOKBACK_DAYS = "180 days ago UTC"


def fetch_and_save(symbol, interval_name, interval):
    print(f"Downloading {symbol} - {interval_name}")

    klines = client.get_historical_klines(
        symbol,
        interval,
        LOOKBACK_DAYS
    )

    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    # Keep only important columns
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]

    # Convert types
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df[["open", "high", "low", "close", "volume"]] = df[
        ["open", "high", "low", "close", "volume"]
    ].astype(float)

    filename = f"{DATA_FOLDER}/{symbol}_{interval_name}.csv"
    df.to_csv(filename, index=False)

    print(f"Saved to {filename}\n")


def main():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    for symbol in SYMBOLS:
        for interval_name, interval in INTERVALS.items():
            fetch_and_save(symbol, interval_name, interval)


if __name__ == "__main__":
    main()