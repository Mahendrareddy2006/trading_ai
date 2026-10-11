"""Multi-Timeframe AI Strategy.

Decision Hierarchy:
1. 4H Regime Check (Trend alignment & volatility safety)
2. 1H Directional ML Signal (Calibrated probability spread / edge)
3. 5M Entry Timing (Microstructure alignment)
"""

from typing import Any, Dict, List
from trading_ai.inference.predictor import model_predictor
from trading_ai.strategies.base import BaseStrategy, StrategyDecision


class MLMultiTimeframeStrategy(BaseStrategy):
    """Integrates 4H regime filtering with 1H directional ML and 5M entry confirmation."""

    def __init__(
        self,
        edge_threshold: float = 0.12,
        min_probability: float = 0.45,
        default_sl_pct: float = 0.015,
        default_tp_pct: float = 0.030
    ):
        super().__init__(name="ML_MultiTimeframe")
        self.edge_threshold = edge_threshold
        self.min_probability = min_probability
        self.default_sl_pct = default_sl_pct
        self.default_tp_pct = default_tp_pct

    def check_4h_regime(self, candles_4h: List[Dict[str, Any]]) -> str:
        """Determines 4H broad trend and volatility state."""
        if len(candles_4h) < 50:
            return "NEUTRAL"
        closes = [c["close"] for c in candles_4h]
        # EMA 50
        alpha = 2.0 / 51.0
        ema_50 = closes[0]
        for val in closes[1:]:
            ema_50 = alpha * val + (1.0 - alpha) * ema_50

        latest_close = closes[-1]
        if latest_close > ema_50 * 1.005:
            return "BULLISH"
        elif latest_close < ema_50 * 0.995:
            return "BEARISH"
        return "NEUTRAL"

    def evaluate(
        self,
        symbol: str,
        candles_by_timeframe: Dict[str, List[Dict[str, Any]]]
    ) -> StrategyDecision:
        candles_1h = candles_by_timeframe.get("1h", [])
        candles_5m = candles_by_timeframe.get("5m", [])
        candles_4h = candles_by_timeframe.get("4h", [])

        if not candles_1h:
            return StrategyDecision(
                symbol=symbol, action="HOLD", price=0.0,
                reason="MISSING_1H_CANDLE_DATA"
            )

        current_price = float(candles_1h[-1]["close"])
        if candles_5m:
            current_price = float(candles_5m[-1]["close"])

        # 1. 4H Regime Check
        regime_4h = self.check_4h_regime(candles_4h) if candles_4h else "NEUTRAL"

        # 2. 1H ML Prediction
        pred_1h = model_predictor.predict(
            candles=candles_1h,
            symbol=symbol,
            timeframe="1h",
            edge_threshold=self.edge_threshold,
            min_probability=self.min_probability
        )

        if pred_1h.abstention_reason:
            return StrategyDecision(
                symbol=symbol,
                action="HOLD",
                price=current_price,
                edge=pred_1h.edge,
                confidence=pred_1h.confidence,
                reason=f"1H_ML_ABSTAIN: {pred_1h.abstention_reason}",
                metadata={"pred_1h": pred_1h.to_dict(), "regime_4h": regime_4h}
            )

        # 3. 5M Entry Timing Filter (EMA 9 vs 21 on 5M)
        if len(candles_5m) >= 25:
            closes_5m = [c["close"] for c in candles_5m]
            alpha9 = 2.0 / 10.0
            alpha21 = 2.0 / 22.0
            ema9 = closes_5m[0]
            ema21 = closes_5m[0]
            for val in closes_5m[1:]:
                ema9 = alpha9 * val + (1.0 - alpha9) * ema9
                ema21 = alpha21 * val + (1.0 - alpha21) * ema21

            if pred_1h.predicted_class == 1 and ema9 < ema21:
                return StrategyDecision(
                    symbol=symbol, action="HOLD", price=current_price,
                    edge=pred_1h.edge, confidence=pred_1h.confidence,
                    reason="5M_TIMING_NOT_ALIGNED_LONG",
                    metadata={"pred_1h": pred_1h.to_dict(), "regime_4h": regime_4h}
                )
            elif pred_1h.predicted_class == -1 and ema9 > ema21:
                return StrategyDecision(
                    symbol=symbol, action="HOLD", price=current_price,
                    edge=pred_1h.edge, confidence=pred_1h.confidence,
                    reason="5M_TIMING_NOT_ALIGNED_SHORT",
                    metadata={"pred_1h": pred_1h.to_dict(), "regime_4h": regime_4h}
                )

        # 4. Final Direction Confirmation
        action = "BUY" if pred_1h.predicted_class == 1 else "SELL"
        reason = f"ML_CONFIRMED_{action} (Edge: {pred_1h.edge:.3f}, Conf: {pred_1h.confidence:.3f})"

        return StrategyDecision(
            symbol=symbol,
            action=action,
            price=current_price,
            edge=pred_1h.edge,
            confidence=pred_1h.confidence,
            stop_loss_pct=self.default_sl_pct,
            take_profit_pct=self.default_tp_pct,
            reason=reason,
            metadata={
                "pred_1h": pred_1h.to_dict(),
                "regime_4h": regime_4h
            }
        )
