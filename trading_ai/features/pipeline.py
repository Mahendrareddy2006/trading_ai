"""Technical Feature Engineering Pipeline.

Computes 100% stationary, scale-independent, leak-free indicators:
- Relative moving average spreads: (close - EMA) / ATR
- Relative trend divergence: (EMA9 - EMA21) / ATR
- Normalized RSI: RSI / 100.0 and RSI changes
- Volatility ratio: ATR / close
- Volume ratios: volume / SMA(volume, 20)
- Momentum: Multi-period returns normalized by ATR
- Candle anatomy: body ratio, upper/lower wick ratios
- Bollinger Band position & width

Runs with native math without fragile external C-extension dependencies.
"""

import math
from typing import Any, Dict, List, Tuple

FEATURE_COLUMNS = [
    "dist_ema_9",
    "dist_ema_21",
    "dist_ema_50",
    "ema_spread_9_21",
    "ema_spread_50_200",
    "rsi_norm",
    "rsi_change",
    "atr_ratio",
    "vol_ratio_20",
    "vol_ratio_50",
    "momentum_3",
    "momentum_6",
    "body_ratio",
    "upper_wick_ratio",
    "lower_wick_ratio",
    "bb_pos",
    "bb_width",
]


def compute_ema(series: List[float], span: int) -> List[float]:
    """Computes Exponential Moving Average with alpha = 2 / (span + 1)."""
    if not series:
        return []
    alpha = 2.0 / (span + 1.0)
    ema = [series[0]]
    for val in series[1:]:
        ema.append(alpha * val + (1.0 - alpha) * ema[-1])
    return ema


def compute_atr(highs: List[float], lows: List[float], closes: List[float], length: int = 14) -> List[float]:
    """Computes Wilder's Average True Range (ATR)."""
    n = len(closes)
    if n == 0:
        return []
    tr = [highs[0] - lows[0]]
    for i in range(1, n):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        tr.append(max(tr1, tr2, tr3))

    alpha = 1.0 / length
    atr = [tr[0]]
    for val in tr[1:]:
        atr.append(alpha * val + (1.0 - alpha) * atr[-1])
    return atr


def compute_rsi(closes: List[float], length: int = 14) -> List[float]:
    """Computes Relative Strength Index (RSI)."""
    n = len(closes)
    if n < 2:
        return [50.0] * n

    gains = [0.0]
    losses = [0.0]
    for i in range(1, n):
        diff = closes[i] - closes[i - 1]
        gains.append(max(0.0, diff))
        losses.append(max(0.0, -diff))

    alpha = 1.0 / length
    avg_gain = [gains[0]]
    avg_loss = [losses[0]]

    for i in range(1, n):
        avg_gain.append(alpha * gains[i] + (1.0 - alpha) * avg_gain[-1])
        avg_loss.append(alpha * losses[i] + (1.0 - alpha) * avg_loss[-1])

    rsi = []
    for g, l in zip(avg_gain, avg_loss):
        if l == 0.0:
            rsi.append(100.0)
        else:
            rs = g / l
            rsi.append(100.0 - (100.0 / (1.0 + rs)))
    return rsi


def compute_sma(series: List[float], window: int) -> List[float]:
    """Computes Simple Moving Average."""
    n = len(series)
    sma = []
    running_sum = 0.0
    for i in range(n):
        running_sum += series[i]
        if i >= window:
            running_sum -= series[i - window]
            sma.append(running_sum / window)
        else:
            sma.append(running_sum / (i + 1))
    return sma


def compute_bollinger_bands(closes: List[float], length: int = 20, num_std: float = 2.0) -> Tuple[List[float], List[float]]:
    """Computes Bollinger Bands upper and lower levels."""
    sma = compute_sma(closes, length)
    upper = []
    lower = []
    for i in range(len(closes)):
        start = max(0, i - length + 1)
        sub = closes[start:i + 1]
        mean = sma[i]
        variance = sum((x - mean) ** 2 for x in sub) / len(sub)
        std = math.sqrt(variance)
        upper.append(mean + num_std * std)
        lower.append(mean - num_std * std)
    return upper, lower


class FeaturePipeline:
    """Transforms raw candlestick dictionaries into stationary feature vectors."""

    def __init__(self, feature_names: List[str] = None):
        self.feature_names = feature_names or FEATURE_COLUMNS

    def transform(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processes candle records and attaches leak-free stationary features."""
        if len(candles) < 30:
            return []

        opens = [c["open"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        volumes = [c.get("volume", 0.0) for c in candles]

        ema_9 = compute_ema(closes, 9)
        ema_21 = compute_ema(closes, 21)
        ema_50 = compute_ema(closes, 50)
        ema_200 = compute_ema(closes, min(200, len(closes)))
        atr_14 = compute_atr(highs, lows, closes, 14)
        rsi_14 = compute_rsi(closes, 14)
        sma_vol_20 = compute_sma(volumes, 20)
        sma_vol_50 = compute_sma(volumes, 50)
        upper_bb, lower_bb = compute_bollinger_bands(closes, 20, 2.0)

        out = []
        # Warmup period 30 bars
        for i in range(30, len(candles)):
            c = candles[i]
            c_open = opens[i]
            c_high = highs[i]
            c_low = lows[i]
            c_close = closes[i]
            c_vol = volumes[i]
            c_atr = max(1e-9, atr_14[i])

            c_range = max(1e-9, c_high - c_low)
            bb_range = max(1e-9, upper_bb[i] - lower_bb[i])

            prev_rsi = rsi_14[i - 1] if i > 0 else rsi_14[i]
            mom_3_price = closes[i - 3] if i >= 3 else closes[0]
            mom_6_price = closes[i - 6] if i >= 6 else closes[0]

            feat = {
                "timestamp": c.get("timestamp"),
                "open": c_open,
                "high": c_high,
                "low": c_low,
                "close": c_close,
                "volume": c_vol,
                # Stationary scale-independent indicators
                "dist_ema_9": (c_close - ema_9[i]) / c_atr,
                "dist_ema_21": (c_close - ema_21[i]) / c_atr,
                "dist_ema_50": (c_close - ema_50[i]) / c_atr,
                "ema_spread_9_21": (ema_9[i] - ema_21[i]) / c_atr,
                "ema_spread_50_200": (ema_50[i] - ema_200[i]) / c_atr,
                "rsi_norm": rsi_14[i] / 100.0,
                "rsi_change": (rsi_14[i] - prev_rsi) / 100.0,
                "atr_ratio": c_atr / max(1e-9, c_close),
                "vol_ratio_20": c_vol / max(1e-9, sma_vol_20[i]),
                "vol_ratio_50": c_vol / max(1e-9, sma_vol_50[i]),
                "momentum_3": (c_close - mom_3_price) / (c_atr * 1.5),
                "momentum_6": (c_close - mom_6_price) / (c_atr * 2.5),
                "body_ratio": abs(c_close - c_open) / c_range,
                "upper_wick_ratio": (c_high - max(c_open, c_close)) / c_range,
                "lower_wick_ratio": (min(c_open, c_close) - c_low) / c_range,
                "bb_pos": (c_close - lower_bb[i]) / bb_range,
                "bb_width": bb_range / max(1e-9, c_close),
            }
            out.append(feat)

        return out

    def extract_matrix(self, features: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[str]]:
        """Extracts numerical matrix X and timestamps."""
        X = []
        timestamps = []
        for r in features:
            timestamps.append(r.get("timestamp", ""))
            row = [float(r.get(col, 0.0)) for col in self.feature_names]
            X.append(row)
        return X, timestamps


feature_pipeline = FeaturePipeline()
