# data_fetcher.py

from binance.client import Client
import pandas as pd
from config import API_KEY, API_SECRET

client = Client(API_KEY, API_SECRET)

def get_data(symbol, interval):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=100)

    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "_","_","_","_","_","_"
    ])

    df["close"] = df["close"].astype(float)
    return df