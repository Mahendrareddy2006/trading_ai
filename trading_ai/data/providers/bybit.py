"""Bybit Public Market Data Provider (Complementary / Fallback).

Integrates Bybit's official public V5 market data endpoints:
- REST Base URL: https://api.bybit.com/v5/market
- Zero API keys or secrets required
- Provides complementary coverage for linear USDT instruments
"""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple
import requests

from trading_ai.core.logging import get_logger
from trading_ai.data.providers.base import BaseMarketDataProvider

logger = get_logger("BybitProvider")

BYBIT_TIMEFRAMES: Dict[str, str] = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "2h": "120",
    "4h": "240",
    "6h": "360",
    "12h": "720",
    "1d": "D",
    "1w": "W"
}


class BybitMarketDataProvider(BaseMarketDataProvider):
    """Client for Bybit's official public V5 market data API."""

    def __init__(self, timeout: float = 8.0):
        self.base_url = "https://api.bybit.com/v5/market"
        self.timeout = timeout
        self._ticker_cache: Dict[str, Dict[str, Any]] = {}
        self._ticker_cache_time: float = 0.0
        self._cache_ttl_sec: float = 1.5

    @property
    def name(self) -> str:
        return "bybit"

    @property
    def display_name(self) -> str:
        return "Bybit Public Market Data"

    def is_symbol_supported(self, symbol: str) -> bool:
        return symbol.upper().endswith("USDT")

    def is_timeframe_supported(self, timeframe: str) -> bool:
        return timeframe.lower() in BYBIT_TIMEFRAMES

    def get_supported_symbols(self) -> List[str]:
        return []

    def get_system_status(self) -> Dict[str, Any]:
        t0 = time.time()
        url = f"{self.base_url}/time"
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            resp = requests.get(url, timeout=4.0)
            latency_ms = round((time.time() - t0) * 1000, 1)
            if resp.status_code == 200 and resp.json().get("retCode") == 0:
                return {
                    "status": "online",
                    "latency_ms": latency_ms,
                    "provider": self.name,
                    "display_name": self.display_name,
                    "endpoint": self.base_url,
                    "credentials_required": False,
                    "last_checked": now_iso
                }
            return {
                "status": "degraded",
                "latency_ms": latency_ms,
                "provider": self.name,
                "display_name": self.display_name,
                "endpoint": self.base_url,
                "credentials_required": False,
                "last_checked": now_iso
            }
        except Exception as e:
            return {
                "status": "offline",
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "error": str(e),
                "provider": self.name,
                "display_name": self.display_name,
                "endpoint": self.base_url,
                "credentials_required": False,
                "last_checked": now_iso
            }

    def fetch_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        now = time.time()
        if self._ticker_cache and (now - self._ticker_cache_time) < self._cache_ttl_sec:
            if symbols:
                target_set = set(symbols)
                return {s: v for s, v in self._ticker_cache.items() if s in target_set}
            return dict(self._ticker_cache)

        url = f"{self.base_url}/tickers"
        params = {"category": "linear"}
        now_iso = datetime.now(timezone.utc).isoformat()
        target_set = set(symbols) if symbols else None
        out: Dict[str, Dict[str, Any]] = {}

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("retCode") == 0:
                    items = data.get("result", {}).get("list", [])
                    for it in items:
                        sym = it.get("symbol")
                        if target_set and sym not in target_set:
                            continue
                        try:
                            last_price = float(it.get("lastPrice", 0.0))
                            change_pct = round(float(it.get("price24hPcnt", 0.0)) * 100, 2)
                            high_price = float(it.get("highPrice24h", 0.0))
                            low_price = float(it.get("lowPrice24h", 0.0))
                            vol_base = round(float(it.get("volume24h", 0.0)), 4)
                            vol_quote = round(float(it.get("turnover24h", 0.0)), 2)
                            mark_price = float(it.get("markPrice", last_price))
                            funding = round(float(it.get("fundingRate", 0.0)) * 100, 4)
                            bid_price = float(it.get("bid1Price", last_price))
                            ask_price = float(it.get("ask1Price", last_price))
                            spread = round(abs(ask_price - bid_price), 4)
                            prev_price = float(it.get("prevPrice24h", last_price))
                            change_abs = round(last_price - prev_price, 4)

                            entry = {
                                "symbol": sym,
                                "market_type": "Perp (Bybit Public)",
                                "price": last_price,
                                "change_24h": change_pct,
                                "change_24h_abs": change_abs,
                                "high_24h": high_price,
                                "low_24h": low_price,
                                "volume_24h": vol_base,
                                "quote_volume_24h": vol_quote,
                                "mark_price": mark_price,
                                "funding_rate": funding,
                                "bid_price": bid_price,
                                "ask_price": ask_price,
                                "spread": spread,
                                "timestamp": now_iso,
                                "is_stale": False
                            }
                            out[sym] = entry
                            self._ticker_cache[sym] = entry
                        except Exception:
                            continue
                    self._ticker_cache_time = now
                    return out
            return self._ticker_cache or {}
        except Exception as e:
            logger.warning(f"Failed to fetch Bybit tickers: {e}")
            return self._ticker_cache or {}

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        bybit_interval = BYBIT_TIMEFRAMES.get(timeframe.lower())
        if not bybit_interval:
            return [], f"Timeframe '{timeframe}' is not supported by Bybit."

        url = f"{self.base_url}/kline"
        params = {
            "category": "linear",
            "symbol": symbol.upper(),
            "interval": bybit_interval,
            "limit": min(limit, 1000)
        }

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("retCode") == 0:
                    raw_list = data.get("result", {}).get("list", [])
                    records = []
                    for k in raw_list:
                        # list item: [startTime_ms, open, high, low, close, volume, turnover]
                        ts = datetime.fromtimestamp(int(k[0]) / 1000.0, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                        records.append({
                            "timestamp": ts,
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "volume": float(k[5]),
                            "is_closed": True
                        })
                    records.sort(key=lambda x: x["timestamp"])
                    return records[-limit:], None
                return [], f"Bybit API error: {data.get('retMsg')}"
            return [], f"Bybit HTTP {resp.status_code}"
        except Exception as e:
            return [], f"Error fetching Bybit candles: {e}"
