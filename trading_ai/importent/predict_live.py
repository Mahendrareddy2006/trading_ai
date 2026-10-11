import pandas as pd
import pandas_ta as ta
from binance.client import Client
import joblib
import numpy as np

# ===== SETTINGS =====
SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_3MINUTE
MODEL_PATH = "models/model_3m.pkl"
# Professional: Use edge instead of raw confidence
EDGE_THRESHOLD = 0.12

client = Client()

# ===== LOAD MODEL =====
model = joblib.load(MODEL_PATH)

FEATURE_COLUMNS = [
    "ema_9",
    "ema_21",
    "ema_9_slope",
    "ema_9_acceleration",
    "range_expansion",
    "volume_spike"
    "rsi",
    "atr",
    "vol_ratio",
    "dist_ema9",
    "rsi_change",
    "momentum_3",
    "body_ratio",
    "atr_ratio"
]


def fetch_latest_data():
    klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=150)

    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    df = df[["timestamp", "open", "high", "low", "close", "volume"]]

    df[["open", "high", "low", "close", "volume"]] = df[
        ["open", "high", "low", "close", "volume"]
    ].astype(float)

    return df


def add_features(df):
    df["ema_9"] = ta.ema(df["close"], length=9)
    df["ema_21"] = ta.ema(df["close"], length=21)
    df["rsi"] = ta.rsi(df["close"], length=14)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]
    df["dist_ema9"] = (df["close"] - df["ema_9"]) / df["ema_9"]

    df["ema_trend"] = (df["ema_9"] > df["ema_21"]).astype(int)
    df["rsi_change"] = df["rsi"].diff()
    df["momentum_3"] = df["close"].pct_change(3)

    df["body_size"] = abs(df["close"] - df["open"])
    df["range_size"] = df["high"] - df["low"]
    df["body_ratio"] = df["body_size"] / df["range_size"]

    df["atr_ratio"] = df["atr"] / df["close"]

    df.dropna(inplace=True)

    return df


def predict():
    df = fetch_latest_data()
    df = add_features(df)

    latest = df.iloc[-1]

    X = pd.DataFrame([latest[FEATURE_COLUMNS].values], columns=FEATURE_COLUMNS)

    probabilities = model.predict_proba(X)[0]

    classes = model.classes_

    prob_dict = dict(zip(classes, probabilities))

    up_prob = prob_dict.get(1, 0)
    down_prob = prob_dict.get(-1, 0)
    
    # Professional: Calculate edge (probability spread)
    edge = up_prob - down_prob
    abs_edge = abs(edge)

    print(f"\nBTCUSDT 3m Prediction (Edge-Based):")
    print(f"UP probability: {up_prob:.3f}")
    print(f"DOWN probability: {down_prob:.3f}")
    print(f"Edge: {edge:.3f}")

    if abs_edge > EDGE_THRESHOLD:
        signal = "🚀 UP SIGNAL" if edge > 0 else "🔻 DOWN SIGNAL"
        print(f"{signal} (edge: {abs_edge:.3f})")
    else:
        print(f"⚠️  Weak edge ({abs_edge:.3f} < {EDGE_THRESHOLD}) - Skip")


if __name__ == "__main__":
    predict()