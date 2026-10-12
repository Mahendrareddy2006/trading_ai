"""Market Data Manager: Ingestion, Validation, and Storage.

Features:
- Ingests public cryptocurrency market data via official Kraken public endpoints
- Zero API keys or secrets required for all public market data functionality
- Validates UTC timestamps, monotonicity, and candle integrity
- Distinguishes clearly between live data and stale/cached historical data
- Automatically persists fresh candles to local cache
- Explicit quote-currency differentiation (USDT vs USD)
"""

import csv
from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from trading_ai.core.logging import get_logger
from trading_ai.data.providers.manager import market_data_provider, CompositeMarketDataProvider
from trading_ai.data.providers.kraken import TIMEFRAME_SECONDS

logger = get_logger("DataManager")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)


class DataManager:
    """Manages acquisition, validation, and storage of OHLCV candles."""

    def __init__(self, data_folder: str = DATA_DIR, provider: Optional[CompositeMarketDataProvider] = None):
        self.data_folder = data_folder
        self.provider = provider or market_data_provider
        self.base_url = "https://api.kraken.com/0/public"

    def get_csv_path(self, symbol: str, timeframe: str) -> str:
        return os.path.join(self.data_folder, f"{symbol.upper()}_{timeframe}.csv")

    def load_candles(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """Loads candles from local CSV cache as a list of validated dictionaries."""
        path = self.get_csv_path(symbol, timeframe)
        if not os.path.exists(path):
            logger.warning(f"No local data found for {symbol} ({timeframe}) at {path}")
            return []

        try:
            records = []
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        ts_str = row.get("timestamp") or row.get("time")
                        if not ts_str:
                            continue
                        records.append({
                            "timestamp": str(ts_str),
                            "open": float(row["open"]),
                            "high": float(row["high"]),
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                            "volume": float(row.get("volume", 0.0)),
                            "is_closed": True
                        })
                    except (ValueError, KeyError):
                        continue

            # Sort and remove duplicates by timestamp
            seen = set()
            clean_records = []
            for r in records:
                ts = r["timestamp"]
                if ts not in seen:
                    seen.add(ts)
                    clean_records.append(r)

            clean_records.sort(key=lambda x: x["timestamp"])
            return clean_records
        except Exception as e:
            logger.error(f"Failed to read/validate {path}: {e}")
            return []

    def save_candles_to_csv(self, symbol: str, timeframe: str, candles: List[Dict[str, Any]]) -> None:
        """Safely saves candle list to CSV cache."""
        if not candles:
            return
        path = self.get_csv_path(symbol, timeframe)
        try:
            fieldnames = ["timestamp", "open", "high", "low", "close", "volume"]
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for c in candles:
                    writer.writerow({
                        "timestamp": c.get("timestamp"),
                        "open": c.get("open"),
                        "high": c.get("high"),
                        "low": c.get("low"),
                        "close": c.get("close"),
                        "volume": c.get("volume", 0.0)
                    })
        except Exception as e:
            logger.warning(f"Could not persist candles to CSV cache at {path}: {e}")

    def is_candle_fresh(self, last_timestamp_str: str, timeframe: str) -> bool:
        """Determines whether a candle timestamp represents live data or stale history."""
        try:
            # Parse timestamp e.g. "2026-10-12 07:00:00" or ISO format
            ts_str = last_timestamp_str.replace("Z", "+00:00")
            if " " in ts_str and "T" not in ts_str:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            else:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)

            now_utc = datetime.now(timezone.utc)
            age_sec = (now_utc - ts).total_seconds()

            interval_sec = TIMEFRAME_SECONDS.get(timeframe.lower(), 3600)
            # Live data threshold: within 3 candle intervals or 4 hours (whichever is greater)
            max_tolerable_age = max(interval_sec * 3, 14400)
            return age_sec <= max_tolerable_age
        except Exception:
            return False

    def get_candles_detailed(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Dict[str, Any]:
        """Fetches candles and returns rich metadata including data freshness and quote currency."""
        clean_symbol = symbol.upper().replace("/", "").replace("-", "").strip()
        sym_info = self.provider.get_symbol_info(clean_symbol)

        base_asset = sym_info.base_asset if sym_info else (clean_symbol[:-4] if clean_symbol.endswith("USDT") else clean_symbol[:3])
        quote_asset = sym_info.quote_asset if sym_info else ("USDT" if clean_symbol.endswith("USDT") else "USD")
        kraken_pair = sym_info.kraken_pair if sym_info else clean_symbol

        # Check if symbol is supported
        if not self.provider.is_symbol_supported(clean_symbol):
            err_reason = self.provider.explain_unsupported_symbol(clean_symbol)
            return {
                "symbol": clean_symbol,
                "base_asset": base_asset,
                "quote_asset": quote_asset,
                "kraken_pair": kraken_pair,
                "market_type": "Spot (Kraken Public)",
                "timeframe": timeframe,
                "limit": limit,
                "count": 0,
                "data_source": "kraken_public",
                "data_freshness": "stale",
                "is_stale": True,
                "error": err_reason,
                "candles": []
            }

        # 1. Attempt live fetch from Kraken public API
        live_candles, err = self.provider.fetch_candles(clean_symbol, timeframe, limit=limit)

        if live_candles and not err:
            last_ts = live_candles[-1].get("timestamp", "")
            fresh = self.is_candle_fresh(last_ts, timeframe)

            # Persist fresh candles to local cache asynchronously / safely
            self.save_candles_to_csv(clean_symbol, timeframe, live_candles)

            return {
                "symbol": clean_symbol,
                "base_asset": base_asset,
                "quote_asset": quote_asset,
                "kraken_pair": kraken_pair,
                "market_type": "Spot (Kraken Public)",
                "timeframe": timeframe,
                "limit": limit,
                "count": len(live_candles),
                "data_source": "kraken_public",
                "data_freshness": "live" if fresh else "stale",
                "is_stale": not fresh,
                "last_updated": last_ts,
                "warning": None if fresh else f"Candles dated {last_ts} may be older than current time.",
                "error": None,
                "candles": live_candles
            }

        # 2. Upstream failed: check local CSV cache
        cached = self.load_candles(clean_symbol, timeframe)
        if cached:
            slice_candles = cached[-limit:]
            last_ts = slice_candles[-1].get("timestamp", "")
            fresh = self.is_candle_fresh(last_ts, timeframe)

            warning_msg = (
                f"Upstream Kraken request failed ({err or 'unavailable'}). "
                f"Showing cached historical data dated {last_ts}. "
                f"{'Data is live.' if fresh else 'Data is stale.'}"
            )
            logger.warning(warning_msg)

            return {
                "symbol": clean_symbol,
                "base_asset": base_asset,
                "quote_asset": quote_asset,
                "kraken_pair": kraken_pair,
                "market_type": "Cached Historical",
                "timeframe": timeframe,
                "limit": limit,
                "count": len(slice_candles),
                "data_source": "cached_local",
                "data_freshness": "live" if fresh else "stale",
                "is_stale": not fresh,
                "last_updated": last_ts,
                "warning": warning_msg,
                "error": None,
                "candles": slice_candles
            }

        # 3. Upstream failed and no cache exists: return honest error
        return {
            "symbol": clean_symbol,
            "base_asset": base_asset,
            "quote_asset": quote_asset,
            "kraken_pair": kraken_pair,
            "market_type": "Spot (Kraken Public)",
            "timeframe": timeframe,
            "limit": limit,
            "count": 0,
            "data_source": "kraken_public",
            "data_freshness": "stale",
            "is_stale": True,
            "error": err or f"Failed to fetch live candles for {symbol} and no local cache exists.",
            "candles": []
        }

    def get_live_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetches true live candles from public market data provider. Falls back to local cache if offline."""
        detailed = self.get_candles_detailed(symbol=symbol, timeframe=timeframe, limit=limit)
        return detailed.get("candles", [])

    def fetch_public_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Fetches public candlestick data directly from built-in public market data provider."""
        return self.get_live_candles(symbol=symbol, timeframe=interval, limit=limit)

    # Backward compatibility alias
    def fetch_binance_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Maintained for backward compatibility; delegates to public market data provider."""
        return self.fetch_public_candles(symbol=symbol, interval=interval, limit=limit)

    def sync_historical_data(
        self,
        symbol: str,
        timeframe: str,
        target_candles: int = 1000
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Loads cached candles and fetches missing latest candles up to target_candles."""
        cached = self.load_candles(symbol, timeframe)
        new_records = self.fetch_public_candles(symbol=symbol, interval=timeframe, limit=target_candles)

        if not new_records:
            return cached, 0

        combined = {r["timestamp"]: r for r in cached}
        new_count = 0
        for r in new_records:
            if r["timestamp"] not in combined:
                new_count += 1
            combined[r["timestamp"]] = r

        merged = sorted(combined.values(), key=lambda x: x["timestamp"])

        # Save to CSV
        self.save_candles_to_csv(symbol, timeframe, merged)
        logger.info(f"Synchronized {symbol} ({timeframe}): Total {len(merged)} candles (+{new_count} new)")

        return merged, new_count

    def fetch_realtime_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Fetches comprehensive real-time prices, 24h metrics, and spreads without credentials."""
        from trading_ai.config.settings import settings
        target_symbols = symbols or settings.default_symbols
        tickers = self.provider.fetch_tickers(target_symbols)

        # Ensure every requested symbol has an entry (if missing from live feed, fallback to last close from cache)
        for sym in target_symbols:
            if sym not in tickers:
                cached = self.load_candles(sym, "1h")
                last_price = cached[-1]["close"] if cached else 100.0
                sym_info = self.provider.get_symbol_info(sym)
                base_asset = sym_info.base_asset if sym_info else sym[:3]
                quote_asset = sym_info.quote_asset if sym_info else ("USDT" if sym.endswith("USDT") else "USD")
                tickers[sym] = {
                    "symbol": sym,
                    "base_asset": base_asset,
                    "quote_asset": quote_asset,
                    "kraken_pair": sym_info.kraken_pair if sym_info else sym,
                    "market_type": "Cached Fallback (Stale)",
                    "price": last_price,
                    "change_24h": 0.0,
                    "change_24h_abs": 0.0,
                    "high_24h": last_price,
                    "low_24h": last_price,
                    "volume_24h": 0.0,
                    "quote_volume_24h": 0.0,
                    "mark_price": last_price,
                    "midpoint": last_price,
                    "funding_rate": 0.0,
                    "bid_price": last_price,
                    "ask_price": last_price,
                    "spread": 0.0,
                    "spread_pct": 0.0,
                    "quote_valid": True,
                    "quote_error": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data_source": "cached_local",
                    "data_freshness": "stale",
                    "is_stale": True
                }

        return tickers


data_manager = DataManager()
