# =========================
# IMPORTS
# =========================

import pandas as pd
import pandas_ta as ta
from binance.client import Client
import joblib

# =========================
# CONFIG
# =========================

SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_1HOUR
MODEL_PATH = "models/model_1h.pkl"
# Professional: Use edge (model spread) instead of absolute confidence
EDGE_THRESHOLD = 0.15  # Minimum difference between UP and DOWN probability

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

# =========================
# FETCH DATA
# =========================

def fetch_1h_data():
    klines = client.get_klines(
        symbol=SYMBOL,
        interval=INTERVAL,
        limit=300
    )

    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    df = df[["open", "high", "low", "close", "volume"]]
    df = df.astype(float)

    return df

# =========================
# FEATURE ENGINEERING
# =========================

def add_features(df):

    # Core indicators
    df["ema_9"] = ta.ema(df["close"], length=9)
    df["ema_21"] = ta.ema(df["close"], length=21)

    df["rsi"] = ta.rsi(df["close"], length=14)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]

    df["dist_ema9"] = (df["close"] - df["ema_9"]) / df["ema_9"]

    # Momentum features
    df["momentum_3"] = df["close"].pct_change(3)
    df["rsi_change"] = df["rsi"].diff()

    # Volatility features
    df["atr_ratio"] = df["atr"] / df["close"]

    # 🔥 MUST MATCH TRAINING
    df["ema_trend_strength"] = (
        (df["ema_9"] - df["ema_21"]) / df["atr"]
    )

    df.dropna(inplace=True)

    return df

# =========================
# PREDICTION
# =========================

def get_edge_signal():
    """
    Professional prediction using EDGE instead of confidence.
    
    Edge = UP_prob - DOWN_prob (measures model conviction/spread)
    
    Returns:
        (edge_value, direction) where direction is 'UP', 'DOWN', or None
    """
    model = joblib.load(MODEL_PATH)

    df = fetch_1h_data()
    df = add_features(df)

    if df.empty:
        print("Not enough data for prediction.")
        return None, None

    latest = df.iloc[-1]

    # Ensure correct feature order
    X = pd.DataFrame(
        [latest[FEATURE_COLUMNS].values],
        columns=FEATURE_COLUMNS
    )

    probabilities = model.predict_proba(X)[0]
    classes = model.classes_
    prob_dict = dict(zip(classes, probabilities))

    up_prob = prob_dict.get(1, 0)
    down_prob = prob_dict.get(-1, 0)
    
    # Professional metric: edge = how much stronger UP is vs DOWN
    edge = up_prob - down_prob  # Range: -1.0 to 1.0
    abs_edge = abs(edge)

    print("\n===== 1H MODEL OUTPUT (EDGE-BASED) =====")
    print(f"UP probability:   {up_prob:.3f}")
    print(f"DOWN probability: {down_prob:.3f}")
    print(f"Edge (spread):    {edge:.3f}")
    print(f"Abs edge:         {abs_edge:.3f}")

    if abs_edge > EDGE_THRESHOLD:
        direction = "UP" if edge > 0 else "DOWN"
        print(f"✅ Strong {direction} edge detected: {abs_edge:.3f}")
        return abs_edge, direction
    else:
        print(f"⚠️  Weak edge ({abs_edge:.3f} < {EDGE_THRESHOLD}) - Skip trade")
        return abs_edge, None

def predict():
    """Backward compatibility wrapper."""
    edge, direction = get_edge_signal()
    return edge, direction

# =========================
# RUN
# =========================

if __name__ == "__main__":
    predict()