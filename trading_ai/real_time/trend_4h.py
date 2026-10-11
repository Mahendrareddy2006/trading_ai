import pandas as pd
import pandas_ta as ta
from binance.client import Client

# ==============================
# CONFIG
# ==============================

SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_4HOUR
LOOKBACK = 300

# Regime detection parameters
TREND_STRENGTH_THRESHOLD = 1.0
ADX_STRONG_TREND = 25        # Strong trend ADX threshold
ADX_WEAK_TREND = 20          # Weak trend ADX threshold
ATR_VOLATILITY_RATIO = 0.02  # High vol if ATR/close > 2%
# Professional: ATR percentile extremes
ATR_PERCENTILE_HIGH = 90     # Skip trading if ATR in top 10% (extreme volatility)
ATR_PERCENTILE_LOW = 10      # Skip trading if ATR in bottom 10% (dead market)

client = Client()


# ==============================
# FETCH DATA
# ==============================

def fetch_4h_data():
    klines = client.get_klines(
        symbol=SYMBOL,
        interval=INTERVAL,
        limit=LOOKBACK
    )

    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    df = df[["open", "high", "low", "close", "volume"]]
    df = df.astype(float)

    return df


# ==============================
# DETECT MARKET REGIME
# ==============================

def detect_regime_filters(df):
    """
    Returns regime analysis tuple:
    (is_trending, is_high_volatility, adx_value, is_extreme_vol)
    
    Professional traders skip trades in:
    - Range-bound markets (ADX < 20)
    - Extreme volatility (ATR in top/bottom 10%)
    - High volatility (ATR/close > threshold)
    """
    
    # ADX for trend strength
    df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
    
    # Volatility measure
    df['atr_ratio'] = df['atr'] / df['close']
    
    latest = df.iloc[-1]
    adx = latest.get('adx', 20)
    vol_ratio = latest['atr_ratio']
    
    # Professional: Check ATR percentile extremes
    atr_percentile = (df['atr'] < df['atr'].iloc[-1]).sum() / len(df) * 100
    is_extreme_vol = (atr_percentile > ATR_PERCENTILE_HIGH or 
                      atr_percentile < ATR_PERCENTILE_LOW)
    
    # Regime flags
    is_trending = adx > ADX_WEAK_TREND
    is_high_vol = vol_ratio > ATR_VOLATILITY_RATIO
    strong_trend = adx > ADX_STRONG_TREND
    
    return is_trending, is_high_vol or is_extreme_vol, adx, strong_trend

# ==============================
# DETECT TREND
# ==============================

def detect_trend():
    df = fetch_4h_data()

    # Core indicators
    df["ema_50"] = ta.ema(df["close"], length=50)
    df["ema_200"] = ta.ema(df["close"], length=200)
    df["rsi"] = ta.rsi(df["close"], length=14)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    # Trend strength relative to volatility
    df["trend_strength"] = (
        (df["ema_50"] - df["ema_200"]) / df["atr"]
    )

    df.dropna(inplace=True)

    latest = df.iloc[-1]
    is_trending, is_high_vol, adx, strong_trend = detect_regime_filters(df)

    print("\n===== 4H TREND ANALYSIS =====")
    print("Close:", round(latest["close"], 2))
    print("EMA 50:", round(latest["ema_50"], 2))
    print("EMA 200:", round(latest["ema_200"], 2))
    print("RSI:", round(latest["rsi"], 2))
    print("Trend Strength:", round(latest["trend_strength"], 2))
    print(f"\n📊 REGIME FILTERS:")
    print(f"ADX: {adx:.1f} (Trend strength)")
    print(f"Is Trending: {is_trending}")
    print(f"High Volatility: {is_high_vol}")
    print(f"Strong Trend: {strong_trend}")

    # ==============================
    # TREND LOGIC WITH REGIME FILTERS
    # ==============================

    # Skip trading in weak trend or high volatility
    if not is_trending:
        print("\n⚠️  REGIME FILTER: Weak trend (ADX < 20) - Skip trading")
        return "RANGE"
    
    if is_high_vol:
        # Professional: Distinguish between high vol and extreme vol
        atr_percentile = (df['atr'] < df['atr'].iloc[-1]).sum() / len(df) * 100
        if atr_percentile > ATR_PERCENTILE_HIGH:
            print(f"\n⚠️  REGIME FILTER: Extreme high volatility (ATR {atr_percentile:.0f}th %ile) - Skip")
        elif atr_percentile < ATR_PERCENTILE_LOW:
            print(f"\n⚠️  REGIME FILTER: Extreme low volatility (ATR {atr_percentile:.0f}th %ile) - Skip")
        else:
            print("\n⚠️  REGIME FILTER: High volatility - Skip trading")
        return "HIGH_VOL"

    # Strong Uptrend
    if (
        latest["trend_strength"] > TREND_STRENGTH_THRESHOLD and
        latest["rsi"] > 55 and
        latest["close"] > latest["ema_200"]
    ):
        print("\n🔥 4H Regime: STRONG UP")
        return "UP"

    # Strong Downtrend
    elif (
        latest["trend_strength"] < -TREND_STRENGTH_THRESHOLD and
        latest["rsi"] < 45 and
        latest["close"] < latest["ema_200"]
    ):
        print("\n🔻 4H Regime: STRONG DOWN")
        return "DOWN"

    # Otherwise sideways/neutral
    else:
        print("\n⚪ 4H Regime: NEUTRAL")
        return "NEUTRAL"


# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    trend = detect_trend()
    print("\nFinal 4H Trend:", trend)