import pandas as pd
import pandas_ta as ta
import os

DATA_FOLDER = "data"

def add_features(df):

    df["ema_9"] = ta.ema(df["close"], length=9)
    df["ema_21"] = ta.ema(df["close"], length=21)

    df["rsi"] = ta.rsi(df["close"], length=14)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]

    df["dist_ema9"] = (df["close"] - df["ema_9"]) / df["ema_9"]

    df["ema_trend_strength"] = (df["ema_9"] - df["ema_21"]) / df["atr"]

    df["momentum_3"] = df["close"].pct_change(3)
    df["rsi_change"] = df["rsi"].diff()

    df["atr_ratio"] = df["atr"] / df["close"]

    df.dropna(inplace=True)

    return df


def process_file(filename):
    df = pd.read_csv(os.path.join(DATA_FOLDER, filename))
    df = add_features(df)
    df.to_csv(os.path.join(DATA_FOLDER, f"features_{filename}"), index=False)


def main():
    for file in os.listdir(DATA_FOLDER):
        if file.endswith("_1h.csv") and not file.startswith("features_"):
            process_file(file)


if __name__ == "__main__":
    main()