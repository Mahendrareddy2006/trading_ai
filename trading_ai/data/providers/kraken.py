"""Kraken Public Market Data Provider.

Integrates Kraken's official public REST API and WebSocket v2 endpoints:
- REST Base URL: https://api.kraken.com/0/public
- WebSocket URL: wss://ws.kraken.com/v2
- Zero API keys or secrets required for all public market data
- Full support for tickers, OHLCV candles, system status, and symbol listings
- Explicit quote-currency differentiation between USDT and fiat USD pairs
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import requests

from trading_ai.core.logging import get_logger
from trading_ai.data.providers.base import BaseMarketDataProvider

logger = get_logger("KrakenProvider")


@dataclass(frozen=True)
class KrakenSymbolInfo:
    """Explicit mapping and metadata for a supported Kraken trading pair."""
    internal_symbol: str      # e.g. "BTCUSDT", "BTCUSD", "ARBUSD"
    kraken_pair: str          # e.g. "XBTUSDT", "XXBTZUSD", "ARBUSD"
    kraken_ws_name: str       # e.g. "XBT/USDT", "XBT/USD", "ARB/USD"
    base_asset: str           # e.g. "BTC", "ETH", "SOL", "ARB"
    quote_asset: str          # "USDT" or "USD"
    description: str          # Human-readable pair description


# Explicit canonical mapping of supported pairs to Kraken specifications.
# Note: Kraken XBT/USD and ARB/USD are fiat USD pairs, whereas XBTUSDT is Tether (USDT).
SUPPORTED_KRAKEN_PAIRS: Dict[str, KrakenSymbolInfo] = {
    # --- USDT (Tether) Quote Pairs ---
    "BTCUSDT": KrakenSymbolInfo("BTCUSDT", "XBTUSDT", "XBT/USDT", "BTC", "USDT", "Bitcoin / Tether"),
    "ETHUSDT": KrakenSymbolInfo("ETHUSDT", "ETHUSDT", "ETH/USDT", "ETH", "USDT", "Ethereum / Tether"),
    "SOLUSDT": KrakenSymbolInfo("SOLUSDT", "SOLUSDT", "SOL/USDT", "SOL", "USDT", "Solana / Tether"),
    "BNBUSDT": KrakenSymbolInfo("BNBUSDT", "BNBUSDT", "BNB/USDT", "BNB", "USDT", "BNB / Tether"),
    "XRPUSDT": KrakenSymbolInfo("XRPUSDT", "XRPUSDT", "XRP/USDT", "XRP", "USDT", "XRP / Tether"),
    "DOGEUSDT": KrakenSymbolInfo("DOGEUSDT", "XDGUSDT", "XDG/USDT", "DOGE", "USDT", "Dogecoin / Tether"),
    "ADAUSDT": KrakenSymbolInfo("ADAUSDT", "ADAUSDT", "ADA/USDT", "ADA", "USDT", "Cardano / Tether"),
    "AVAXUSDT": KrakenSymbolInfo("AVAXUSDT", "AVAXUSDT", "AVAX/USDT", "AVAX", "USDT", "Avalanche / Tether"),
    "LINKUSDT": KrakenSymbolInfo("LINKUSDT", "LINKUSDT", "LINK/USDT", "LINK", "USDT", "Chainlink / Tether"),
    "DOTUSDT": KrakenSymbolInfo("DOTUSDT", "DOTUSDT", "DOT/USDT", "DOT", "USDT", "Polkadot / Tether"),
    "LTCUSDT": KrakenSymbolInfo("LTCUSDT", "LTCUSDT", "LTC/USDT", "LTC", "USDT", "Litecoin / Tether"),
    "BCHUSDT": KrakenSymbolInfo("BCHUSDT", "BCHUSDT", "BCH/USDT", "BCH", "USDT", "Bitcoin Cash / Tether"),
    "ATOMUSDT": KrakenSymbolInfo("ATOMUSDT", "ATOMUSDT", "ATOM/USDT", "ATOM", "USDT", "Cosmos / Tether"),
    "SHIBUSDT": KrakenSymbolInfo("SHIBUSDT", "SHIBUSDT", "SHIB/USDT", "SHIB", "USDT", "Shiba Inu / Tether"),

    # --- USD (Fiat US Dollar) Quote Pairs ---
    "BTCUSD": KrakenSymbolInfo("BTCUSD", "XXBTZUSD", "XBT/USD", "BTC", "USD", "Bitcoin / US Dollar (Fiat)"),
    "XBTUSD": KrakenSymbolInfo("XBTUSD", "XXBTZUSD", "XBT/USD", "BTC", "USD", "Bitcoin / US Dollar (Fiat)"),
    "ETHUSD": KrakenSymbolInfo("ETHUSD", "XETHZUSD", "ETH/USD", "ETH", "USD", "Ethereum / US Dollar (Fiat)"),
    "SOLUSD": KrakenSymbolInfo("SOLUSD", "SOLUSD", "SOL/USD", "SOL", "USD", "Solana / US Dollar (Fiat)"),
    "DOGEUSD": KrakenSymbolInfo("DOGEUSD", "XDGUSD", "XDG/USD", "DOGE", "USD", "Dogecoin / US Dollar (Fiat)"),
    "XRPUSD": KrakenSymbolInfo("XRPUSD", "XXRPZUSD", "XRP/USD", "XRP", "USD", "XRP / US Dollar (Fiat)"),
    "ADAUSD": KrakenSymbolInfo("ADAUSD", "ADAUSD", "ADA/USD", "ADA", "USD", "Cardano / US Dollar (Fiat)"),
    "AVAXUSD": KrakenSymbolInfo("AVAXUSD", "AVAXUSD", "AVAX/USD", "AVAX", "USD", "Avalanche / US Dollar (Fiat)"),
    "LINKUSD": KrakenSymbolInfo("LINKUSD", "LINKUSD", "LINK/USD", "LINK", "USD", "Chainlink / US Dollar (Fiat)"),
    "DOTUSD": KrakenSymbolInfo("DOTUSD", "DOTUSD", "DOT/USD", "DOT", "USD", "Polkadot / US Dollar (Fiat)"),
    "LTCUSD": KrakenSymbolInfo("LTCUSD", "XLTCZUSD", "LTC/USD", "LTC", "USD", "Litecoin / US Dollar (Fiat)"),
    "BCHUSD": KrakenSymbolInfo("BCHUSD", "BCHUSD", "BCH/USD", "BCH", "USD", "Bitcoin Cash / US Dollar (Fiat)"),
    "ATOMUSD": KrakenSymbolInfo("ATOMUSD", "ATOMUSD", "ATOM/USD", "ATOM", "USD", "Cosmos / US Dollar (Fiat)"),
    "ARBUSD": KrakenSymbolInfo("ARBUSD", "ARBUSD", "ARB/USD", "ARB", "USD", "Arbitrum / US Dollar (Fiat)"),
    "SUIUSD": KrakenSymbolInfo("SUIUSD", "SUIUSD", "SUI/USD", "SUI", "USD", "Sui / US Dollar (Fiat)"),
    "NEARUSD": KrakenSymbolInfo("NEARUSD", "NEARUSD", "NEAR/USD", "NEAR", "USD", "NEAR Protocol / US Dollar (Fiat)"),
}

# Reverse lookup dictionary: Kraken response keys / altnames -> internal symbol
KRAKEN_PAIR_TO_SYMBOL: Dict[str, str] = {
    # USDT response keys
    "XBTUSDT": "BTCUSDT",
    "XXBTZUSDT": "BTCUSDT",
    "ETHUSDT": "ETHUSDT",
    "XETHZUSDT": "ETHUSDT",
    "SOLUSDT": "SOLUSDT",
    "BNBUSDT": "BNBUSDT",
    "XRPUSDT": "XRPUSDT",
    "XXRPZUSDT": "XRPUSDT",
    "XDGUSDT": "DOGEUSDT",
    "XXDGZUSDT": "DOGEUSDT",
    "ADAUSDT": "ADAUSDT",
    "AVAXUSDT": "AVAXUSDT",
    "LINKUSDT": "LINKUSDT",
    "DOTUSDT": "DOTUSDT",
    "LTCUSDT": "LTCUSDT",
    "XLTCZUSDT": "LTCUSDT",
    "BCHUSDT": "BCHUSDT",
    "ATOMUSDT": "ATOMUSDT",
    "SHIBUSDT": "SHIBUSDT",

    # USD response keys
    "XXBTZUSD": "BTCUSD",
    "XBTUSD": "BTCUSD",
    "XETHZUSD": "ETHUSD",
    "ETHUSD": "ETHUSD",
    "SOLUSD": "SOLUSD",
    "XDGUSD": "DOGEUSD",
    "XXDGZUSD": "DOGEUSD",
    "XXRPZUSD": "XRPUSD",
    "XRPUSD": "XRPUSD",
    "ADAUSD": "ADAUSD",
    "AVAXUSD": "AVAXUSD",
    "LINKUSD": "LINKUSD",
    "DOTUSD": "DOTUSD",
    "XLTCZUSD": "LTCUSD",
    "LTCUSD": "LTCUSD",
    "BCHUSD": "BCHUSD",
    "ATOMUSD": "ATOMUSD",
    "ARBUSD": "ARBUSD",
    "SUIUSD": "SUIUSD",
    "NEARUSD": "NEARUSD",
}

# Kraken OHLC intervals in minutes
TIMEFRAME_TO_KRAKEN_INTERVAL: Dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
    "1w": 10080,
    "15d": 21600,
}

TIMEFRAME_SECONDS: Dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}


class KrakenMarketDataProvider(BaseMarketDataProvider):
    """Production client for Kraken's official public market data API."""

    def __init__(self, timeout: float = 8.0):
        self.base_url = "https://api.kraken.com/0/public"
        self.ws_url = "wss://ws.kraken.com/v2"
        self.timeout = timeout

        # Short-lived in-memory caches to protect against rate limits and provide sub-millisecond responses
        self._ticker_cache: Dict[str, Dict[str, Any]] = {}
        self._ticker_cache_time: float = 0.0
        self._cache_ttl_sec: float = 1.5

        # Track last successful API update
        self._last_successful_update: Optional[str] = None

        logger.info("Initialized KrakenMarketDataProvider (Public API, zero credentials required)")

    @property
    def name(self) -> str:
        return "kraken"

    @property
    def display_name(self) -> str:
        return "Kraken Public Market Data (Spot)"

    @property
    def last_successful_update(self) -> Optional[str]:
        return self._last_successful_update

    def map_symbol_to_kraken(self, symbol: str) -> Optional[str]:
        """Translates standard symbol (e.g. 'BTCUSDT' or 'BTCUSD') to Kraken REST pair identifier ('XBTUSDT')."""
        clean = symbol.upper().replace("/", "").replace("-", "").strip()
        info = SUPPORTED_KRAKEN_PAIRS.get(clean)
        if info:
            return info.kraken_pair
        if clean in KRAKEN_PAIR_TO_SYMBOL:
            return clean
        return None

    def get_symbol_info(self, symbol: str) -> Optional[KrakenSymbolInfo]:
        """Returns metadata for a supported symbol."""
        clean = symbol.upper().replace("/", "").replace("-", "").strip()
        return SUPPORTED_KRAKEN_PAIRS.get(clean)

    def map_kraken_to_symbol(self, kraken_key: str) -> str:
        """Translates Kraken response key back to standard symbol (e.g. 'XBTUSDT' -> 'BTCUSDT')."""
        clean = kraken_key.upper().strip()
        if clean in KRAKEN_PAIR_TO_SYMBOL:
            return KRAKEN_PAIR_TO_SYMBOL[clean]
        # Standard fallback if ending in USDT
        if clean.endswith("USDT"):
            if clean.startswith("X") and len(clean) > 5 and clean[1:-4] in ["BT", "RP", "LTC"]:
                if clean == "XBTUSDT":
                    return "BTCUSDT"
                if clean == "XXRPUSDT":
                    return "XRPUSDT"
            return clean
        return clean

    def is_symbol_supported(self, symbol: str) -> bool:
        clean = symbol.upper().replace("/", "").replace("-", "").strip()
        return clean in SUPPORTED_KRAKEN_PAIRS or clean in KRAKEN_PAIR_TO_SYMBOL

    def is_timeframe_supported(self, timeframe: str) -> bool:
        return timeframe.lower() in TIMEFRAME_TO_KRAKEN_INTERVAL

    def get_supported_symbols(self) -> List[str]:
        return list(SUPPORTED_KRAKEN_PAIRS.keys())

    def explain_unsupported_symbol(self, symbol: str) -> str:
        """Provides an explicit explanation of why a symbol is unsupported and guides the user."""
        clean = symbol.upper().replace("/", "").replace("-", "").strip()
        if clean == "ARBUSDT":
            return (
                "Symbol 'ARBUSDT' (quote: USDT) is not listed on Kraken Spot. "
                "Kraken provides 'ARBUSD' (quote: USD). "
                "Never silently substituting USD data for USDT data. "
                "Please request 'ARBUSD' to view Arbitrum market data, or select a supported USDT pair."
            )
        if clean == "SUIUSDT":
            return (
                "Symbol 'SUIUSDT' (quote: USDT) is not listed on Kraken Spot. "
                "Kraken provides 'SUIUSD' (quote: USD). "
                "Please request 'SUIUSD' to view Sui market data."
            )
        if clean == "NEARUSDT":
            return (
                "Symbol 'NEARUSDT' (quote: USDT) is not listed on Kraken Spot. "
                "Kraken provides 'NEARUSD' (quote: USD). "
                "Please request 'NEARUSD' to view Near market data."
            )
        if clean.endswith("USDT") and clean[:-4] + "USD" in SUPPORTED_KRAKEN_PAIRS:
            usd_sym = clean[:-4] + "USD"
            return (
                f"Symbol '{symbol}' (quote: USDT) is not listed on Kraken Spot. "
                f"Kraken provides '{usd_sym}' (quote: USD). "
                f"Please request '{usd_sym}' for USD market data."
            )
        return (
            f"Symbol '{symbol}' is not supported by Kraken public market data. "
            f"Supported pairs: {', '.join(sorted(list(SUPPORTED_KRAKEN_PAIRS.keys())[:10]))}..."
        )

    # =========================================================================
    # System Status & Health
    # =========================================================================

    def get_system_status(self) -> Dict[str, Any]:
        """Checks Kraken API system status and latency directly."""
        t0 = time.time()
        url = f"{self.base_url}/SystemStatus"
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            resp = requests.get(url, timeout=4.0)
            latency_ms = round((time.time() - t0) * 1000, 1)
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result", {})
                status_str = result.get("status", "online")
                self._last_successful_update = now_iso
                return {
                    "status": "online" if status_str == "online" else status_str,
                    "latency_ms": latency_ms,
                    "provider": self.name,
                    "display_name": self.display_name,
                    "endpoint": self.base_url,
                    "credentials_required": False,
                    "last_checked": now_iso,
                    "last_successful_update": self._last_successful_update
                }
            else:
                return {
                    "status": "degraded",
                    "latency_ms": latency_ms,
                    "error": f"HTTP {resp.status_code}",
                    "provider": self.name,
                    "display_name": self.display_name,
                    "endpoint": self.base_url,
                    "credentials_required": False,
                    "last_checked": now_iso,
                    "last_successful_update": self._last_successful_update
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
                "last_checked": now_iso,
                "last_successful_update": self._last_successful_update
            }

    # =========================================================================
    # Tickers
    # =========================================================================

    def parse_ticker_item(
        self,
        std_sym: str,
        k_key: str,
        item: Dict[str, Any],
        timestamp_iso: str
    ) -> Dict[str, Any]:
        """Parses a single Kraken ticker item payload with strict bid/ask and spread validations.
        
        Kraken official Ticker payload format:
        - 'a': Ask [<price>, <whole lot volume>, <lot volume>]
        - 'b': Bid [<price>, <whole lot volume>, <lot volume>]
        - 'c': Last trade closed [<price>, <lot volume>]
        - 'v': Volume [<today>, <last 24 hours>]
        - 'p': Volume weighted average price [<today>, <last 24 hours>]
        - 't': Number of trades [<today>, <last 24 hours>]
        - 'l': Low [<today>, <last 24 hours>]
        - 'h': High [<today>, <last 24 hours>]
        - 'o': Today's opening price
        """
        sym_info = self.get_symbol_info(std_sym)
        base_asset = sym_info.base_asset if sym_info else (std_sym[:-4] if std_sym.endswith("USDT") else std_sym[:3])
        quote_asset = sym_info.quote_asset if sym_info else ("USDT" if std_sym.endswith("USDT") else "USD")

        try:
            # 1. Parse raw prices without premature rounding
            last_price = float(item["c"][0])
            open_price = float(item.get("o", last_price))
            high_price = float(item["h"][1])
            low_price = float(item["l"][1])
            vol_base = float(item["v"][1])
            vwap = float(item["p"][1]) if float(item["p"][1]) > 0 else last_price
            vol_quote = vol_base * vwap

            # 2. Extract best ask from 'a' and best bid from 'b' (Kraken official spec)
            # Never swap values to make an invalid quote look valid!
            ask_price = float(item["a"][0])
            bid_price = float(item["b"][0])

            # 3. Validate quotes & calculate spread without premature rounding
            quote_valid = True
            quote_error = None

            if math.isnan(bid_price) or math.isnan(ask_price) or math.isinf(bid_price) or math.isinf(ask_price):
                quote_valid = False
                quote_error = f"Non-finite quote values: bid={bid_price}, ask={ask_price}"
                logger.warning(f"Invalid market quote for {std_sym} ({k_key}): {quote_error}")
            elif bid_price <= 0 or ask_price <= 0:
                quote_valid = False
                quote_error = f"Non-positive quote values: bid={bid_price}, ask={ask_price}"
                logger.warning(f"Invalid market quote for {std_sym} ({k_key}): {quote_error}")
            elif ask_price < bid_price:
                # Crossed market quote from upstream source
                quote_valid = False
                quote_error = f"Crossed quote from upstream source: ask ({ask_price}) < bid ({bid_price})"
                logger.warning(f"Crossed market quote for {std_sym} ({k_key}): {quote_error}")

            if quote_valid:
                spread = ask_price - bid_price
                midpoint = (ask_price + bid_price) / 2.0
                spread_pct = ((ask_price - bid_price) / midpoint * 100.0) if midpoint > 0 else 0.0
            else:
                spread = 0.0
                spread_pct = 0.0
                midpoint = last_price

            change_abs = last_price - open_price
            change_pct = ((last_price - open_price) / open_price * 100.0) if open_price > 0 else 0.0

            return {
                "symbol": std_sym,
                "base_asset": base_asset,
                "quote_asset": quote_asset,
                "kraken_pair": k_key,
                "market_type": "Spot (Kraken Public)",
                "price": last_price,
                "change_24h": round(change_pct, 4),
                "change_24h_abs": round(change_abs, 8),
                "high_24h": high_price,
                "low_24h": low_price,
                "volume_24h": round(vol_base, 4),
                "quote_volume_24h": round(vol_quote, 2),
                "mark_price": round(midpoint, 8) if quote_valid else last_price,
                "midpoint": round(midpoint, 8),
                "funding_rate": 0.0,
                "bid_price": bid_price,
                "ask_price": ask_price,
                "spread": round(spread, 8),
                "spread_pct": round(spread_pct, 4),
                "quote_valid": quote_valid,
                "quote_error": quote_error,
                "timestamp": timestamp_iso,
                "data_source": "kraken_public",
                "data_freshness": "live" if quote_valid else "invalid_quote",
                "is_stale": not quote_valid
            }
        except (KeyError, ValueError, IndexError, TypeError) as parse_err:
            logger.warning(f"Malformed Kraken ticker item for {k_key}: {parse_err}")
            return {
                "symbol": std_sym,
                "base_asset": base_asset,
                "quote_asset": quote_asset,
                "kraken_pair": k_key,
                "market_type": "Spot (Kraken Public)",
                "price": 0.0,
                "change_24h": 0.0,
                "change_24h_abs": 0.0,
                "high_24h": 0.0,
                "low_24h": 0.0,
                "volume_24h": 0.0,
                "quote_volume_24h": 0.0,
                "mark_price": 0.0,
                "midpoint": 0.0,
                "funding_rate": 0.0,
                "bid_price": 0.0,
                "ask_price": 0.0,
                "spread": 0.0,
                "spread_pct": 0.0,
                "quote_valid": False,
                "quote_error": f"Malformed payload from upstream: {parse_err}",
                "timestamp": timestamp_iso,
                "data_source": "kraken_public",
                "data_freshness": "malformed_quote",
                "is_stale": True
            }

    def fetch_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Fetches real-time ticker statistics from Kraken's public Ticker endpoint."""
        now = time.time()
        # Return memory cache if within TTL
        if self._ticker_cache and (now - self._ticker_cache_time) < self._cache_ttl_sec:
            if symbols:
                target_set = set(symbols)
                return {s: v for s, v in self._ticker_cache.items() if s in target_set}
            return dict(self._ticker_cache)

        target_symbols = symbols or list(SUPPORTED_KRAKEN_PAIRS.keys())
        kraken_pairs = []
        pair_to_std: Dict[str, str] = {}

        for sym in target_symbols:
            k_key = self.map_symbol_to_kraken(sym)
            if k_key:
                kraken_pairs.append(k_key)
                pair_to_std[k_key] = sym

        if not kraken_pairs:
            logger.warning("No supported Kraken pairs found in request")
            return {}

        url = f"{self.base_url}/Ticker"
        params = {"pair": ",".join(kraken_pairs)}
        now_iso = datetime.now(timezone.utc).isoformat()
        out: Dict[str, Dict[str, Any]] = {}

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                body = resp.json()
                errors = body.get("error", [])
                if errors:
                    logger.warning(f"Kraken Ticker API returned warnings/errors: {errors}")

                result = body.get("result", {})
                for k_key, item in result.items():
                    std_sym = pair_to_std.get(k_key) or self.map_kraken_to_symbol(k_key)
                    ticker_entry = self.parse_ticker_item(std_sym, k_key, item, now_iso)
                    out[std_sym] = ticker_entry
                    self._ticker_cache[std_sym] = ticker_entry

                self._ticker_cache_time = now
                self._last_successful_update = now_iso
                return out
            else:
                logger.error(f"Kraken Ticker API HTTP {resp.status_code}: {resp.text}")
                return self._ticker_cache or {}
        except Exception as e:
            logger.error(f"Network error fetching Kraken tickers: {e}")
            return self._ticker_cache or {}

    # =========================================================================
    # OHLCV Candles
    # =========================================================================

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetches OHLCV candlestick data from Kraken's official public OHLC endpoint."""
        clean = symbol.upper().replace("/", "").replace("-", "").strip()
        if not self.is_symbol_supported(clean):
            err = self.explain_unsupported_symbol(clean)
            logger.warning(err)
            return [], err

        kraken_pair = self.map_symbol_to_kraken(clean)
        if not kraken_pair:
            err = self.explain_unsupported_symbol(clean)
            return [], err

        interval_min = TIMEFRAME_TO_KRAKEN_INTERVAL.get(timeframe.lower())
        if interval_min is None:
            err = (
                f"Timeframe '{timeframe}' is not supported by Kraken OHLC. "
                f"Supported timeframes: {list(TIMEFRAME_TO_KRAKEN_INTERVAL.keys())}"
            )
            logger.warning(err)
            return [], err

        url = f"{self.base_url}/OHLC"
        params = {
            "pair": kraken_pair,
            "interval": interval_min
        }

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                body = resp.json()
                errors = body.get("error", [])
                if errors:
                    err_msg = "; ".join(errors)
                    logger.error(f"Kraken OHLC error: {err_msg}")
                    return [], f"Kraken API error: {err_msg}"

                result = body.get("result", {})
                pair_keys = [k for k in result.keys() if k != "last"]
                if not pair_keys:
                    return [], f"No candle data returned by Kraken for pair '{kraken_pair}'"

                raw_candles = result[pair_keys[0]]
                records: List[Dict[str, Any]] = []

                for k in raw_candles:
                    try:
                        # k: [time, open, high, low, close, vwap, volume, count]
                        unix_sec = int(k[0])
                        ts = datetime.fromtimestamp(unix_sec, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                        records.append({
                            "timestamp": ts,
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "volume": float(k[6]),
                            "is_closed": True
                        })
                    except (ValueError, IndexError, KeyError):
                        continue

                # Sort chronologically ascending
                records.sort(key=lambda x: x["timestamp"])

                # Respect requested limit
                if limit and limit > 0:
                    records = records[-limit:]

                self._last_successful_update = datetime.now(timezone.utc).isoformat()
                return records, None
            else:
                err_msg = f"Kraken OHLC HTTP {resp.status_code}: {resp.text}"
                logger.error(err_msg)
                return [], err_msg
        except requests.exceptions.Timeout:
            err_msg = f"Timeout connecting to Kraken OHLC endpoint for {symbol} ({timeframe})"
            logger.warning(err_msg)
            return [], err_msg
        except Exception as e:
            err_msg = f"Network exception fetching Kraken candles: {e}"
            logger.error(err_msg)
            return [], err_msg
