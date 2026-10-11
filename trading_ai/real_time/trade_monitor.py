import pandas as pd
from binance.client import Client
from trading_ai.real_time.telegram_alert import send_alert
from datetime import datetime

SYMBOL = "BTCUSDT"

client = Client()


# =========================
# GET LIVE PRICE
# =========================
def fetch_latest_price():
    ticker = client.get_symbol_ticker(symbol=SYMBOL)
    return float(ticker["price"])


# =========================
# MONITOR TRADES
# =========================
def monitor_trades():

    try:
        df = pd.read_csv("trade_log.csv")
    except FileNotFoundError:
        print("No trades yet.")
        return

    if df.empty:
        print("No trades to monitor.")
        return

    required_columns = ["direction", "entry", "tp", "sl", "status"]

    for col in required_columns:
        if col not in df.columns:
            print(f"Missing column in CSV: {col}")
            return

    price = fetch_latest_price()
    print(f"Current Price: {price}")

    trade_updated = False

    for i, row in df.iterrows():

        if row["status"] == "OPEN":

            direction = row["direction"]
            entry = float(row["entry"])
            tp = float(row["tp"])
            sl = float(row["sl"])

            # =====================
            # LONG TRADE
            # =====================
            if direction == "LONG":

                if price >= tp:
                    pnl = price - entry
                    df.at[i, "status"] = "CLOSED"
                    df.at[i, "result"] = "WIN"
                    df.at[i, "exit_price"] = price
                    df.at[i, "closed_time"] = datetime.utcnow()

                    send_alert(
                        f"🎯 TP HIT (LONG)\n"
                        f"Entry: {entry}\n"
                        f"Exit: {price}\n"
                        f"PnL: {round(pnl, 2)}"
                    )

                    trade_updated = True

                elif price <= sl:
                    pnl = price - entry
                    df.at[i, "status"] = "CLOSED"
                    df.at[i, "result"] = "LOSS"
                    df.at[i, "exit_price"] = price
                    df.at[i, "closed_time"] = datetime.utcnow()

                    send_alert(
                        f"❌ SL HIT (LONG)\n"
                        f"Entry: {entry}\n"
                        f"Exit: {price}\n"
                        f"PnL: {round(pnl, 2)}"
                    )

                    trade_updated = True

            # =====================
            # SHORT TRADE
            # =====================
            elif direction == "SHORT":

                if price <= tp:
                    pnl = entry - price
                    df.at[i, "status"] = "CLOSED"
                    df.at[i, "result"] = "WIN"
                    df.at[i, "exit_price"] = price
                    df.at[i, "closed_time"] = datetime.utcnow()

                    send_alert(
                        f"🎯 TP HIT (SHORT)\n"
                        f"Entry: {entry}\n"
                        f"Exit: {price}\n"
                        f"PnL: {round(pnl, 2)}"
                    )

                    trade_updated = True

                elif price >= sl:
                    pnl = entry - price
                    df.at[i, "status"] = "CLOSED"
                    df.at[i, "result"] = "LOSS"
                    df.at[i, "exit_price"] = price
                    df.at[i, "closed_time"] = datetime.utcnow()

                    send_alert(
                        f"❌ SL HIT (SHORT)\n"
                        f"Entry: {entry}\n"
                        f"Exit: {price}\n"
                        f"PnL: {round(pnl, 2)}"
                    )

                    trade_updated = True

    if trade_updated:
        df.to_csv("trade_log.csv", index=False)
        print("Trade status updated and saved.")
    else:
        print("No TP/SL hit yet.")


# =========================
# RUN STANDALONE
# =========================
if __name__ == "__main__":
    monitor_trades()