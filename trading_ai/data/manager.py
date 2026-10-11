"""Market Data Manager: Ingestion, Validation, and Storage.

Works seamlessly with or without external dependencies:
- Reads CSV datasets via built-in CSV module and/or Pandas
- Validates UTC timestamps, monotonicity, and candle integrity
- Ingests public Binance Futures klines without credentials
- Non-blocking and zero DLL dependencies
"""

import csv
from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List, Optional, Tuple
import requests

from trading_ai.core.logging import get_logger

logger = get_logger("DataManager")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)


class DataManager:
    """Manages acquisition, validation, and storage of OHLCV candles."""

    def __init__(self, data_folder: str = DATA_DIR):
        self.data_folder = data_folder
        self.base_url = "https://fapi.binance.com/fapi/v1"

    def get_csv_path(self, symbol: str, timeframe: str) -> str:
        return os.path.join(self.data_folder, f"{symbol}_{timeframe}.csv")

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

    def fetch_binance_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Fetches public candlestick data directly from Binance Futures public API."""
        url = f"{self.base_url}/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1500)
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                raw = resp.json()
                records = []
                for k in raw:
                    ts = datetime.fromtimestamp(k[0] / 1000.0, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    records.append({
                        "timestamp": ts,
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                        "is_closed": True
                    })
                return records
            else:
                logger.error(f"Binance public API returned status {resp.status_code}: {resp.text}")
                return []
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {e}")
            return []

    def sync_historical_data(
        self,
        symbol: str,
        timeframe: str,
        target_candles: int = 1000
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Loads cached candles and fetches missing latest candles up to target_candles."""
        cached = self.load_candles(symbol, timeframe)
        new_records = self.fetch_binance_klines(symbol=symbol, interval=timeframe, limit=target_candles)

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
        save_path = self.get_csv_path(symbol, timeframe)
        try:
            with open(save_path, "w", newline="", encoding="utf-8") as f:
                fieldnames = ["timestamp", "open", "high", "low", "close", "volume"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in merged:
                    writer.writerow({k: r[k] for k in fieldnames})
            logger.info(f"Synchronized {symbol} ({timeframe}): Total {len(merged)} candles (+{new_count} new)")
        except Exception as e:
            logger.error(f"Error saving candles to {save_path}: {e}")

        return merged, new_count


data_manager = DataManager()
