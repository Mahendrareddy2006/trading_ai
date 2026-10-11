import pandas as pd
import pandas_ta as ta
from binance.client import Client
import joblib
import csv
import os
from datetime import datetime

# =========================
# CONFIG
# =========================

SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_5MINUTE


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "model_5m.pkl")
# Professional: Use edge threshold instead of raw confidence
EDGE_THRESHOLD = 0.12  # Minimum probability spread for 5M entry

RISK_PERCENT = 0.003      # 0.3%
REWARD_PERCENT = 0.006    # 0.6%

FEATURE_COLUMNS = [
    "ema_9",
    "ema_21",
    "rsi",
    "atr",
    "vol_ratio",
    "dist_ema9",
    "ema_trend_strength",
    "momentum_3",
    "rsi_change",
    "atr_ratio"
]

client = Client()
model = joblib.load(MODEL_PATH)


# =========================
# LOG TRADE
# =========================

def log_trade(SYMBOL, direction, entry_price, tp, sl):

    if direction == "LONG":
        tp = entry_price * (1 + REWARD_PERCENT)
        sl = entry_price * (1 - RISK_PERCENT)
    else:
        tp = entry_price * (1 - REWARD_PERCENT)
        sl = entry_price * (1 + RISK_PERCENT)

    with open("trade_log.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            datetime.utcnow(),
            SYMBOL,
            direction,
            entry_price,
            tp,
            sl,
            "OPEN",
            "",     # result
            "",     # exit_price
            ""      # closed_time
        ])

    print("📁 Trade logged successfully.")


# =========================
# FETCH DATA
# =========================

def fetch_5m_data():

    klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=200)

    df = pd.DataFrame(klines, columns=[
        "timestamp","open","high","low","close","volume",
        "close_time","quote_asset_volume","number_of_trades",
        "taker_buy_base","taker_buy_quote","ignore"
    ])

    df = df[["open","high","low","close","volume"]]
    df = df.astype(float)

    return df


# =========================
# ADD FEATURES
# =========================

def add_features(df):

    df["ema_9"] = ta.ema(df["close"], length=9)
    df["ema_21"] = ta.ema(df["close"], length=21)

    df["rsi"] = ta.rsi(df["close"], length=14)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]

    df["dist_ema9"] = (df["close"] - df["ema_9"]) / df["ema_9"]
    df["momentum_3"] = df["close"].pct_change(3)
    df["rsi_change"] = df["rsi"].diff()
    df["atr_ratio"] = df["atr"] / df["close"]

    df["ema_trend_strength"] = (df["ema_9"] - df["ema_21"]) / df["atr"]

    df.dropna(inplace=True)

    return df


# =========================
# ENTRY CHECK
# =========================

def check_entry(direction):

    df = fetch_5m_data()
    df = add_features(df)

    latest = df.iloc[-1]

    current_price = latest["close"]

    # =============================
    # RULE FILTER
    # =============================

    if direction == "LONG":
        rule_pass = (
            latest["ema_9"] > latest["ema_21"] and
            latest["ema_trend_strength"] > 0 and
            latest["rsi"] > 45
        )
    else:
        rule_pass = (
            latest["ema_9"] < latest["ema_21"] and
            latest["ema_trend_strength"] < 0 and
            latest["rsi"] < 55
        )

    if not rule_pass:
        print("❌ 5M rule filter rejected entry.")
        return False

    # =============================
    # ML CONFIRMATION
    # =============================

    X = pd.DataFrame(
        [latest[FEATURE_COLUMNS].values],
        columns=FEATURE_COLUMNS
    )

    probs = model.predict_proba(X)[0]
    classes = model.classes_
    prob_dict = dict(zip(classes, probs))

    up_prob = prob_dict.get(1, 0)
    down_prob = prob_dict.get(-1, 0)
    
    # Professional: Use edge (probability spread) instead of absolute confidence
    edge = abs(up_prob - down_prob)

    if direction == "LONG":
        if up_prob > down_prob and edge > EDGE_THRESHOLD:
            print(f"✅ 5M LONG ENTRY CONFIRMED (Edge: {edge:.3f})")
            log_trade("LONG", current_price)
            return True

    if direction == "SHORT":
        if down_prob > up_prob and edge > EDGE_THRESHOLD:
            print(f"✅ 5M SHORT ENTRY CONFIRMED (Edge: {edge:.3f})")
            log_trade("SHORT", current_price)
            return True

    print(f"❌ 5M ML filter rejected (weak edge: {edge:.3f})")
    return False