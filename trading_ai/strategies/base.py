"""Canonical Strategy Interface.

All strategies (rule-based and ML-based) implement BaseStrategy to ensure
consistent output schemas, testability, and decoupled execution.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class StrategyDecision:
    """Standardized strategy decision object."""

    def __init__(
        self,
        symbol: str,
        action: str,  # "BUY", "SELL", or "HOLD"
        price: float,
        edge: float = 0.0,
        confidence: float = 0.0,
        stop_loss_pct: float = 0.015,
        take_profit_pct: float = 0.030,
        reason: str = "NO_SIGNAL",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.symbol = symbol
        self.action = action.upper()
        self.price = price
        self.edge = edge
        self.confidence = confidence
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.reason = reason
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "price": self.price,
            "edge": round(self.edge, 4),
            "confidence": round(self.confidence, 4),
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "reason": self.reason,
            "metadata": self.metadata
        }


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def evaluate(
        self,
        symbol: str,
        candles_by_timeframe: Dict[str, List[Dict[str, Any]]]
    ) -> StrategyDecision:
        """Evaluates market state and returns a canonical StrategyDecision."""
        pass
