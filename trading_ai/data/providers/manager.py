"""Composite Market Data Provider Manager.

Coordinates built-in public market data providers:
- Primary: KrakenMarketDataProvider (Spot official public endpoints)
- Secondary / Fallback: BybitMarketDataProvider (linear USDT public endpoints)
- Zero credentials required for all public market data functionality
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from trading_ai.core.logging import get_logger
from trading_ai.data.providers.base import BaseMarketDataProvider
from trading_ai.data.providers.kraken import KrakenMarketDataProvider, KrakenSymbolInfo
from trading_ai.data.providers.bybit import BybitMarketDataProvider

logger = get_logger("MarketDataProviderManager")


class CompositeMarketDataProvider(BaseMarketDataProvider):
    """Manages primary and fallback public market data providers."""

    def __init__(self, primary_provider_name: str = "kraken"):
        self.kraken = KrakenMarketDataProvider()
        self.bybit = BybitMarketDataProvider()
        self.primary_name = primary_provider_name.lower()
        self._last_active_provider = self.primary_name

        logger.info(f"Initialized CompositeMarketDataProvider. Primary: {self.primary_name.upper()}")

    @property
    def name(self) -> str:
        return "composite"

    @property
    def display_name(self) -> str:
        return self.kraken.display_name if self.primary_name == "kraken" else self.bybit.display_name

    @property
    def primary_provider(self) -> BaseMarketDataProvider:
        if self.primary_name == "bybit":
            return self.bybit
        return self.kraken

    @property
    def secondary_provider(self) -> BaseMarketDataProvider:
        if self.primary_name == "bybit":
            return self.kraken
        return self.bybit

    def is_symbol_supported(self, symbol: str) -> bool:
        if self.primary_name == "kraken":
            return self.kraken.is_symbol_supported(symbol)
        return self.kraken.is_symbol_supported(symbol) or self.bybit.is_symbol_supported(symbol)

    def is_timeframe_supported(self, timeframe: str) -> bool:
        return self.primary_provider.is_timeframe_supported(timeframe)

    def get_supported_symbols(self) -> List[str]:
        return self.kraken.get_supported_symbols()

    def get_symbol_info(self, symbol: str) -> Optional[KrakenSymbolInfo]:
        return self.kraken.get_symbol_info(symbol)

    def explain_unsupported_symbol(self, symbol: str) -> str:
        return self.kraken.explain_unsupported_symbol(symbol)

    def get_system_status(self) -> Dict[str, Any]:
        """Checks primary provider health and returns comprehensive data-status."""
        primary_status = self.primary_provider.get_system_status()
        secondary_status = self.secondary_provider.get_system_status()

        is_online = primary_status.get("status") == "online"
        last_update = primary_status.get("last_successful_update") or secondary_status.get("last_successful_update")
        return {
            "status": "online" if is_online else primary_status.get("status", "offline"),
            "latency_ms": primary_status.get("latency_ms", 0),
            "primary_provider": {
                "name": self.primary_provider.name,
                "display_name": self.primary_provider.display_name,
                "status": primary_status.get("status", "unknown"),
                "latency_ms": primary_status.get("latency_ms", 0),
                "endpoint": "https://api.kraken.com/0/public",
                "credentials_required": False
            },
            "fallback_provider": {
                "name": self.secondary_provider.name,
                "display_name": self.secondary_provider.display_name,
                "status": secondary_status.get("status", "unknown"),
                "latency_ms": secondary_status.get("latency_ms", 0),
                "credentials_required": False
            },
            "credentials_required": False,
            "last_active_provider": self._last_active_provider,
            "last_successful_update": last_update,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def fetch_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Fetches tickers from primary provider (Kraken)."""
        kraken_tickers = self.kraken.fetch_tickers(symbols)
        result: Dict[str, Dict[str, Any]] = dict(kraken_tickers)

        # Fallback to secondary only if primary returned empty and caller configured fallback
        if not result and symbols and self.primary_name != "kraken":
            logger.info("Primary provider returned empty tickers; checking secondary provider")
            result = self.bybit.fetch_tickers(symbols)
            self._last_active_provider = self.secondary_provider.name
        else:
            self._last_active_provider = self.primary_provider.name

        return result

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetches candles directly from primary provider (Kraken)."""
        if self.primary_name == "kraken":
            return self.kraken.fetch_candles(symbol, timeframe, limit=limit)

        # Fallback logic if composite allows secondary
        if self.primary_provider.is_symbol_supported(symbol):
            candles, err = self.primary_provider.fetch_candles(symbol, timeframe, limit=limit)
            if candles and not err:
                self._last_active_provider = self.primary_provider.name
                return candles, None

        if self.secondary_provider.is_symbol_supported(symbol):
            candles, err = self.secondary_provider.fetch_candles(symbol, timeframe, limit=limit)
            if candles and not err:
                self._last_active_provider = self.secondary_provider.name
                return candles, None

        return [], self.explain_unsupported_symbol(symbol)


# Canonical singleton provider
market_data_provider = CompositeMarketDataProvider(primary_provider_name="kraken")
