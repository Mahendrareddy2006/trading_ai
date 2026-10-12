"""Market Data Provider Abstraction.

Defines the base interface for public cryptocurrency market data providers.
Allows the Trading AI platform to ingest tickers, OHLCV candles, and orderbook depth
from official public exchange APIs without requiring user registration or API credentials.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class BaseMarketDataProvider(ABC):
    """Abstract base class for public market data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'kraken', 'bybit')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name (e.g. 'Kraken Public Market Data')."""
        pass

    @property
    def requires_credentials(self) -> bool:
        """Public market data providers never require API keys or secrets."""
        return False

    @abstractmethod
    def get_system_status(self) -> Dict[str, Any]:
        """Checks provider health, connectivity status, and round-trip latency."""
        pass

    @abstractmethod
    def fetch_tickers(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetches 24h ticker metrics for requested symbols.
        
        Returns a dictionary mapping standard symbol (e.g. 'BTCUSDT') to standardized ticker dict:
        {
            "symbol": "BTCUSDT",
            "market_type": "Spot (Kraken Public)",
            "price": float,
            "change_24h": float,
            "change_24h_abs": float,
            "high_24h": float,
            "low_24h": float,
            "volume_24h": float,
            "quote_volume_24h": float,
            "mark_price": float,
            "funding_rate": float,
            "bid_price": float,
            "ask_price": float,
            "spread": float,
            "timestamp": iso_str,
            "is_stale": bool
        }
        """
        pass

    @abstractmethod
    def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetches historical and latest OHLCV candles.
        
        Returns tuple of (candles, error_message).
        Each candle record contains:
        {
            "timestamp": "YYYY-MM-DD HH:MM:SS",
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": float,
            "is_closed": bool
        }
        """
        pass

    @abstractmethod
    def is_symbol_supported(self, symbol: str) -> bool:
        """Returns True if the provider supports the given symbol."""
        pass

    @abstractmethod
    def is_timeframe_supported(self, timeframe: str) -> bool:
        """Returns True if the provider supports the given timeframe."""
        pass

    @abstractmethod
    def get_supported_symbols(self) -> List[str]:
        """Returns list of standard symbols supported by this provider."""
        pass
