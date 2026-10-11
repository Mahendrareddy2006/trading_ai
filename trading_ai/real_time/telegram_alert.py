from binance.client import Client
import pandas as pd
import requests
import time
import os

# =========================
# CONFIG (Use Environment Variables)
# =========================
API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_1MINUTE

client = Client(API_KEY, API_SECRET)

# =========================
# TELEGRAM FUNCTION
# =========================
def send_alert(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("[Telegram Alert Disabled / No Credentials]:", message)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(url, data=data)
        print("📨 Telegram Status:", response.status_code)
    except Exception as e:
        print("❌ Telegram Error:", e)

# Backward-compatibility alias
send_telegram = send_alert



# =========================
# EMA STRATEGY FUNCTION
# =========================
def check_signal():
    klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=50)

    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "_","_","_","_","_","_"
    ])

    df["close"] = df["close"].astype(float)

    # Proper EMA calculation
    df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    # Cross above → LONG
    if previous["ema9"] < previous["ema21"] and latest["ema9"] > latest["ema21"]:
        return "LONG", latest["close"]

    # Cross below → SHORT
    if previous["ema9"] > previous["ema21"] and latest["ema9"] < latest["ema21"]:
        return "SHORT", latest["close"]

    return None, None


# =========================
# MAIN LOOP (NEW CANDLE ONLY)
# =========================
def run_bot():
    print("🚀 EMA Bot Started")
    last_signal = None
    last_candle_time = None

    while True:
        try:
            # Get latest candle timestamp
            latest_kline = client.get_klines(
                symbol=SYMBOL,
                interval=INTERVAL,
                limit=1
            )

            current_candle_time = latest_kline[0][0]

            # Only check when new candle appears
            if current_candle_time != last_candle_time:
                last_candle_time = current_candle_time

                signal, price = check_signal()

                if signal and signal != last_signal:
                    message = (
                        f"{signal} SIGNAL 🚀\n"
                        f"Symbol: {SYMBOL}\n"
                        f"Price: {round(price, 2)}"
                    )

                    print(message)
                    send_telegram(message)

                    last_signal = signal
                else:
                    print("No new crossover signal.")

            time.sleep(5)

        except Exception as e:
            print("⚠ Error:", e)
            time.sleep(10)


# =========================
# START BOT
# =========================
if __name__ == "__main__":
    run_bot()