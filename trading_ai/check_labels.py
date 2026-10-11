import pandas as pd

df = pd.read_csv("data/labeled_features_BTCUSDT_3m.csv")

print(df["label"].value_counts())