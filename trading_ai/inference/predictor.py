"""Unified Inference Engine.

Produces standardized prediction outputs:
- Probabilities for BUY, SELL, NEUTRAL
- Directional Edge: p_buy - p_sell
- Prediction Confidence
- Market Regime status
- Explicit Abstention Reasons
"""

from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional
import joblib

from trading_ai.core.logging import get_logger
from trading_ai.features.pipeline import FEATURE_COLUMNS, feature_pipeline

logger = get_logger("Predictor")
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_models")


class PredictionResult:
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        predicted_class: int,
        probabilities: Dict[str, float],
        edge: float,
        confidence: float,
        regime: str,
        abstention_reason: Optional[str] = None,
        model_version: str = "v1.0"
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.predicted_class = predicted_class
        self.probabilities = probabilities
        self.edge = edge
        self.confidence = confidence
        self.regime = regime
        self.abstention_reason = abstention_reason
        self.model_version = model_version
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "predicted_class": self.predicted_class,
            "direction": "LONG" if self.predicted_class == 1 else ("SHORT" if self.predicted_class == -1 else "NEUTRAL"),
            "probabilities": self.probabilities,
            "edge": round(self.edge, 4),
            "confidence": round(self.confidence, 4),
            "regime": self.regime,
            "abstention_reason": self.abstention_reason,
            "model_version": self.model_version,
            "timestamp": self.timestamp
        }


class ModelPredictor:
    def __init__(self, models_dir: str = MODELS_DIR):
        self.models_dir = models_dir
        self._cached_models: Dict[str, Dict[str, Any]] = {}

    def get_latest_model_bundle(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        key = f"{symbol}_{timeframe}"
        if key in self._cached_models:
            return self._cached_models[key]

        if not os.path.exists(self.models_dir):
            return None

        candidates = [
            f for f in os.listdir(self.models_dir)
            if f.startswith(f"{symbol}_{timeframe}_") and f.endswith(".joblib")
        ]
        if not candidates:
            candidates = [
                f for f in os.listdir(self.models_dir)
                if f.startswith(f"{symbol}_") and f.endswith(".joblib")
            ]

        if not candidates:
            return None

        candidates.sort(reverse=True)
        latest_path = os.path.join(self.models_dir, candidates[0])
        try:
            bundle = joblib.load(latest_path)
            self._cached_models[key] = bundle
            return bundle
        except Exception as e:
            logger.error(f"Failed to load model {latest_path}: {e}")
            return None

    def predict(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        edge_threshold: float = 0.12,
        min_probability: float = 0.45
    ) -> PredictionResult:
        bundle = self.get_latest_model_bundle(symbol, timeframe)
        if bundle is None:
            return PredictionResult(
                symbol=symbol,
                timeframe=timeframe,
                predicted_class=0,
                probabilities={"BUY": 0.33, "SELL": 0.33, "NEUTRAL": 0.34},
                edge=0.0,
                confidence=0.34,
                regime="UNKNOWN",
                abstention_reason="NO_TRAINED_MODEL_AVAILABLE",
                model_version="NONE"
            )

        model = bundle["model"]
        classes = bundle.get("classes", [-1, 0, 1])
        model_id = bundle.get("model_id", "v1.0")

        features = feature_pipeline.transform(candles)
        if not features:
            return PredictionResult(
                symbol=symbol,
                timeframe=timeframe,
                predicted_class=0,
                probabilities={"BUY": 0.33, "SELL": 0.33, "NEUTRAL": 0.34},
                edge=0.0,
                confidence=0.34,
                regime="UNKNOWN",
                abstention_reason="INSUFFICIENT_CANDLES_FOR_FEATURES",
                model_version=model_id
            )

        latest_feature = features[-1]
        x_row = [float(latest_feature.get(col, 0.0)) for col in FEATURE_COLUMNS]

        raw_probas = model.predict_proba([x_row])[0]
        prob_dict = dict(zip(classes, raw_probas))

        p_buy = float(prob_dict.get(1, 0.0))
        p_sell = float(prob_dict.get(-1, 0.0))
        p_neutral = float(prob_dict.get(0, 0.0))

        edge = p_buy - p_sell
        abs_edge = abs(edge)
        confidence = max(p_buy, p_sell, p_neutral)

        atr_ratio = float(latest_feature.get("atr_ratio", 0.01))
        ema_spread = float(latest_feature.get("ema_spread_50_200", 0.0))

        if atr_ratio > 0.025:
            regime = "HIGH_VOLATILITY"
        elif abs(ema_spread) < 0.2:
            regime = "RANGE_BOUND"
        elif ema_spread > 0.5:
            regime = "BULL_TREND"
        elif ema_spread < -0.5:
            regime = "BEAR_TREND"
        else:
            regime = "NORMAL"

        abstention = None
        predicted_class = 0

        if regime == "HIGH_VOLATILITY":
            abstention = "REGIME_HIGH_VOLATILITY_ABSTAIN"
        elif abs_edge < edge_threshold:
            abstention = f"EDGE_TOO_LOW ({abs_edge:.3f} < {edge_threshold})"
        elif max(p_buy, p_sell) < min_probability:
            abstention = f"PROBABILITY_TOO_LOW ({max(p_buy, p_sell):.3f} < {min_probability})"
        else:
            predicted_class = 1 if edge > 0 else -1

        return PredictionResult(
            symbol=symbol,
            timeframe=timeframe,
            predicted_class=predicted_class,
            probabilities={"BUY": round(p_buy, 4), "SELL": round(p_sell, 4), "NEUTRAL": round(p_neutral, 4)},
            edge=edge,
            confidence=confidence,
            regime=regime,
            abstention_reason=abstention,
            model_version=model_id
        )


model_predictor = ModelPredictor()
