import pandas as pd
import os
import numpy as np

DATA_FOLDER = "data"

LOOKAHEAD = 3        # 12 hours

def add_labels(df):
    """
    Professional label distribution using percentiles instead of fixed threshold.
    
    Top 30% of returns → Label 1 (BUY)
    Bottom 30% of returns → Label -1 (SELL)
    Middle 40% → Dropped (eliminate sideways/neutral trades)
    
    This creates balanced, meaningful labels that reflect market distribution.
    """
    df["future_close"] = df["close"].shift(-LOOKAHEAD)
    df["future_return"] = (df["future_close"] - df["close"]) / df["close"]

    # Calculate 33rd and 67th percentiles
    p33 = df["future_return"].quantile(0.33)
    p67 = df["future_return"].quantile(0.67)

    df["label"] = 0
    df.loc[df["future_return"] > p67, "label"] = 1   # Top 33% → UP
    df.loc[df["future_return"] < p33, "label"] = -1  # Bottom 33% → DOWN

    # Remove middle 33% (neutral trades - sideways markets)
    df = df[df["label"] != 0].copy()

    df.drop(columns=["future_close", "future_return"], inplace=True)
    df.dropna(inplace=True)

    return df


def main():
    for file in os.listdir(DATA_FOLDER):
        if file.startswith("features_") and file.endswith("_1h.csv"):
            df = pd.read_csv(os.path.join(DATA_FOLDER, file))
            df = add_labels(df)
            df.to_csv(os.path.join(DATA_FOLDER, f"labeled_{file}"), index=False)


if __name__ == "__main__":
    main()