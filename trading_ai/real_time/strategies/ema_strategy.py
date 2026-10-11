import pandas as pd
from binance.client import Client
from trading_ai.real_time.api_manager import safe_api_call
from trading_ai.real_time.strategies.base_strategy import BaseStrategy


class EMAStrategy(BaseStrategy):

    def __init__(self, interval=Client.KLINE_INTERVAL_1MINUTE):
        self.interval = interval

    # =====================================================
    # BACKTEST MODE SIGNAL (uses existing dataframe)
    # =====================================================
    def generate_signal_from_df(self, df):
        """
        Professional edition: Returns edge instead of confidence.
        
        Edge = model_conviction = how strongly EMA is positioned
        """

        if len(df) < 21:
            return None, None, None

        df = df.copy()

        df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        # Edge = how much EMA9 is above/below EMA21 (normalized)
        ema_diff = (latest["ema9"] - latest["ema21"]) / latest["ema21"]
        edge = abs(ema_diff)  # Range 0.0 to 1.0+

        if previous["ema9"] < previous["ema21"] and latest["ema9"] > latest["ema21"]:
            return "LONG", latest["close"], edge

        if previous["ema9"] > previous["ema21"] and latest["ema9"] < latest["ema21"]:
            return "SHORT", latest["close"], edge

        return None, None, None

    # =====================================================
    # LIVE MODE SIGNAL (fetches Binance data)
    # =====================================================
    def generate_signal(self, client, symbol):

        klines = safe_api_call(
            client.futures_klines,
            symbol=symbol,
            interval=self.interval,
            limit=50
        )

        if not klines:
            return None, None, None

        df = pd.DataFrame(klines, columns=[
            "time", "open", "high", "low", "close", "volume",
            "_", "_", "_", "_", "_", "_"
        ])

        df["close"] = df["close"].astype(float)

        return self.generate_signal_from_df(df)