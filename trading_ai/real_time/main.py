# main.py

import time
import pandas as pd
import requests
from datetime import datetime

from config import SYMBOLS, INTERVAL
from data_fetcher import get_data
from strategy import apply_indicators, check_signal
from risk_management import calculate_sl_tp
from entry_5m import log_trade
from telegram_alert import send_telegram
from position_sizing import calculate_position_size


# =========================
# N8N WEBHOOK SENDER
# =========================
def send_to_n8n(symbol, direction, entry, sl, tp, confidence):

    # 🔥 USE PRODUCTION URL (NO -test)
    webhook_url = "https://workflow.ccbp.in/webhook/84b33d1a-be27-434b-b071-6b1bddd529a4"

    data = {
        "time": str(datetime.utcnow()),
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "confidence": confidence,
        "status": "OPEN"
    }

    try:
        response = requests.post(webhook_url, json=data)
        print("📡 Sent to n8n:", response.status_code)
    except Exception as e:
        print("❌ Failed to send to n8n:", e)


# =========================
# CHECK IF SYMBOL HAS OPEN TRADE
# =========================
def has_open_trade(symbol):
    try:
        df = pd.read_csv("trade_log.csv")
    except:
        return False

    if df.empty:
        return False

    open_trades = df[
        (df["symbol"] == symbol) &
        (df["status"] == "OPEN")
    ]

    return not open_trades.empty


# =========================
# MAIN ENGINE LOOP
# =========================
def run_engine():

    print("🚀 Multi-Coin Trading Engine Started")

    last_signals = {symbol: None for symbol in SYMBOLS}

    while True:
        try:
            for symbol in SYMBOLS:

                print(f"\n🔎 Scanning {symbol}...")

                # Skip if trade already open
                if has_open_trade(symbol):
                    print(f"⚠ {symbol} already has OPEN trade. Skipping.")
                    continue

                # Fetch and prepare data
                df = get_data(symbol, INTERVAL)
                df = apply_indicators(df)

                signal = check_signal(df)

                if signal and signal != last_signals[symbol]:

                    entry = float(df.iloc[-1]["close"])
                    sl, tp = calculate_sl_tp(signal, entry)

                    quantity = calculate_position_size(entry, sl)

                    if quantity <= 0:
                        print("⚠ Position size calculation failed.")
                        continue

                    message = (
                        f"📢 {symbol} {signal} SIGNAL\n"
                        f"Entry: {round(entry, 2)}\n"
                        f"SL: {round(sl, 2)}\n"
                        f"TP: {round(tp, 2)}\n"
                        f"Size: {quantity}"
                    )

                    print(message)

                    # Send Telegram
                    send_telegram(message)

                    # Send to n8n (Google Sheets logging)
                    confidence = 0.75  # Replace with real ML probability later
                    send_to_n8n(symbol, signal, entry, sl, tp, confidence)

                    # Log locally
                    log_trade(symbol, signal, entry, sl, tp, quantity)

                    last_signals[symbol] = signal

                else:
                    print(f"No valid signal for {symbol}")

            time.sleep(30)

        except Exception as e:
            print("⚠ Engine Error:", e)
            time.sleep(10)


# =========================
# START ENGINE
# =========================
if __name__ == "__main__":
    run_engine()
