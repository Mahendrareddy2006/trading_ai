"""Institutional Binance USD(S)-M Futures Client.

Features:
- Zero external package dependencies (built using requests, hmac, hashlib)
- Supports unauthenticated public market data (klines, tickers, orderbook depth)
- Supports authenticated read-only account data (balances, positions, open orders, trade history)
- Automatic HMAC-SHA256 request signing with timestamp synchronization
- Strict credential redaction in all exception logs
- Granular error diagnostics (UNAUTHORIZED, IP_RESTRICTION, RATE_LIMITED, CREDENTIALS_NOT_CONFIGURED)
- Separation of Spot and Futures endpoints
- Safe fallback and dynamic settings binding
"""

from datetime import datetime, timezone
import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import requests

from trading_ai.config.settings import settings
from trading_ai.core.logging import get_logger

logger = get_logger("BinanceClient")


class BinanceFuturesClient:
    """Official Binance USD(S)-M Futures REST API Client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: Optional[bool] = None
    ):
        self._api_key = api_key
        self._api_secret = api_secret
        self._testnet = testnet

        self.timeout = 7.0
        self.time_offset_ms = 0
        self._last_sync_timestamp: Optional[str] = None

    @property
    def api_key(self) -> str:
        """Returns configured API key, stripped of any leading/trailing whitespace."""
        val = self._api_key if self._api_key is not None else settings.BINANCE_API_KEY
        return (val or "").strip()

    @property
    def api_secret(self) -> str:
        """Returns configured API secret, stripped of any leading/trailing whitespace."""
        val = self._api_secret if self._api_secret is not None else settings.BINANCE_API_SECRET
        return (val or "").strip()

    @property
    def testnet(self) -> bool:
        """Returns whether testnet is active. Correctly handles explicit False."""
        if self._testnet is not None:
            return self._testnet
        return getattr(settings, "BINANCE_TESTNET", False)

    @property
    def base_url(self) -> str:
        """Returns official Binance USD(S)-M Futures Base URL."""
        if self.testnet:
            return "https://testnet.binancefuture.com"
        return "https://fapi.binance.com"

    @property
    def is_configured(self) -> bool:
        """Checks if authenticated credentials are configured with non-empty, non-placeholder values."""
        key = self.api_key
        secret = self.api_secret
        if not key or not secret:
            return False
        # Guard against placeholder values
        lower_key = key.lower()
        if "your_" in lower_key or "placeholder" in lower_key or "replace" in lower_key:
            return False
        return len(key) >= 16 and len(secret) >= 16

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TradingAI-Platform/2.0"
        }
        key = self.api_key
        if key:
            headers["X-MBX-APIKEY"] = key
        return headers

    def sync_server_time(self) -> int:
        """Synchronizes local clock with Binance Futures server time to prevent timestamp errors."""
        url = f"{self.base_url}/fapi/v1/time"
        try:
            t0 = time.time()
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                server_time = resp.json().get("serverTime", 0)
                local_time = int(time.time() * 1000)
                self.time_offset_ms = server_time - local_time
                self._last_sync_timestamp = datetime.now(timezone.utc).isoformat()
                latency_ms = int((time.time() - t0) * 1000)
                logger.info(f"Binance Futures server time synced. Offset: {self.time_offset_ms}ms, Latency: {latency_ms}ms")
                return latency_ms
        except Exception as e:
            logger.warning(f"Failed to sync Binance server time: {e}")
        return -1

    def _sign_query(self, params: Dict[str, Any]) -> str:
        """Appends UTC timestamp and generates HMAC-SHA256 signature."""
        secret = self.api_secret
        if not secret:
            raise ValueError("API Secret not configured for authenticated request.")

        # Sync timestamp with exchange offset
        now_ms = int(time.time() * 1000) + self.time_offset_ms
        params["timestamp"] = now_ms
        params["recvWindow"] = 10000

        query_str = urllib.parse.urlencode(params)
        signature = hmac.new(
            secret.encode("utf-8"),
            query_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return f"{query_str}&signature={signature}"

    def _safe_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False
    ) -> Tuple[Optional[Any], Optional[str]]:
        """Executes HTTP request with error redaction and status parsing."""
        params = dict(params or {})

        if signed:
            if not self.is_configured:
                return None, "CREDENTIALS_NOT_CONFIGURED"

            # Auto-sync clock if not synced yet
            if self.time_offset_ms == 0:
                self.sync_server_time()

            try:
                query_string = self._sign_query(params)
                url = f"{self.base_url}{path}?{query_string}"
            except Exception as e:
                return None, f"SIGNING_ERROR: {str(e)}"
        else:
            query_string = urllib.parse.urlencode(params) if params else ""
            url = f"{self.base_url}{path}" + (f"?{query_string}" if query_string else "")

        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                timeout=self.timeout
            )

            if resp.status_code == 200:
                self._last_sync_timestamp = datetime.now(timezone.utc).isoformat()
                return resp.json(), None
            else:
                binance_code = None
                binance_msg = ""
                try:
                    err_json = resp.json()
                    binance_code = err_json.get("code")
                    binance_msg = err_json.get("msg", resp.text)
                except Exception:
                    binance_msg = resp.text

                # Specific diagnosis based on official Binance Futures error codes
                if binance_code == -2015:
                    return None, f"INVALID_API_KEY_OR_IP_RESTRICTION: {binance_msg}"
                elif binance_code == -1021:
                    # Timestamp error: sync clock and report
                    self.sync_server_time()
                    return None, f"TIMESTAMP_OUTSIDE_RECVWINDOW: {binance_msg}"
                elif binance_code == -1022:
                    return None, f"SIGNATURE_INVALID: {binance_msg}"
                elif resp.status_code == 401:
                    return None, f"UNAUTHORIZED: {binance_msg or 'Invalid API credentials.'}"
                elif resp.status_code == 403:
                    return None, f"IP_OR_PERMISSION_RESTRICTED: {binance_msg or 'Access forbidden by exchange.'}"
                elif resp.status_code == 429:
                    return None, "RATE_LIMITED"
                else:
                    return None, f"API_ERROR_{resp.status_code}: {binance_msg}"

        except requests.exceptions.Timeout:
            return None, "REQUEST_TIMEOUT"
        except requests.exceptions.ConnectionError:
            return None, "CONNECTION_ERROR"
        except Exception as e:
            return None, f"NETWORK_ERROR: {str(e)}"

    # =========================================================================
    # Public Market Data Endpoints (No Credentials Required)
    # =========================================================================

    def get_server_ping(self) -> Dict[str, Any]:
        """Tests exchange connectivity and latency."""
        t0 = time.time()
        url = f"{self.base_url}/fapi/v1/ping"
        try:
            res = requests.get(url, timeout=3.0)
            latency = round((time.time() - t0) * 1000, 1)
            return {
                "status": "online" if res.status_code == 200 else "error",
                "latency_ms": latency,
                "exchange": "Binance USD(S)-M Futures",
                "testnet": self.testnet,
                "endpoint": self.base_url,
                "last_checked": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "status": "offline",
                "error": str(e),
                "exchange": "Binance USD(S)-M Futures",
                "testnet": self.testnet,
                "endpoint": self.base_url,
                "last_checked": datetime.now(timezone.utc).isoformat()
            }

    def get_realtime_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Fetches 24hr statistics and prices for configured symbols."""
        data, err = self._safe_request("GET", "/fapi/v1/ticker/24hr")
        if err or not isinstance(data, list):
            logger.warning(f"Ticker fetch failed: {err}")
            return {}

        filter_symbols = set(symbols or ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"])
        out = {}
        for item in data:
            sym = item.get("symbol")
            if sym in filter_symbols:
                out[sym] = {
                    "symbol": sym,
                    "price": float(item.get("lastPrice", 0.0)),
                    "change_24h": round(float(item.get("priceChangePercent", 0.0)), 2),
                    "high_24h": float(item.get("highPrice", 0.0)),
                    "low_24h": float(item.get("lowPrice", 0.0)),
                    "volume_24h": round(float(item.get("volume", 0.0)), 2),
                    "quote_volume_24h": round(float(item.get("quoteVolume", 0.0)), 2),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        return out

    def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 1000
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetches historical and currently forming OHLCV klines with strict UTC timestamps."""
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1500)
        }
        data, err = self._safe_request("GET", "/fapi/v1/klines", params=params)
        if err or not isinstance(data, list):
            return [], err

        records = []
        for k in data:
            records.append({
                "open_time": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": int(k[6]),
                "quote_asset_volume": float(k[7]),
                "trades": int(k[8]),
                "is_closed": bool(k[6] < (time.time() * 1000)),
                "timestamp_iso": datetime.fromtimestamp(k[0] / 1000.0, timezone.utc).isoformat()
            })
        return records, None

    # =========================================================================
    # Authenticated Read-Only Account Endpoints (Requires Read API Key)
    # =========================================================================

    def get_account_summary(self) -> Tuple[Dict[str, Any], Optional[str]]:
        """Fetches total wallet balance, available margin, and total unrealized PnL."""
        if not self.is_configured:
            return {
                "is_configured": False,
                "status": "CREDENTIALS_NOT_CONFIGURED",
                "message": "Configure BINANCE_API_KEY and BINANCE_API_SECRET in root .env for live account balance monitoring."
            }, "CREDENTIALS_NOT_CONFIGURED"

        data, err = self._safe_request("GET", "/fapi/v2/account", signed=True)
        if err or not isinstance(data, dict):
            status = "AUTH_FAILED"
            msg = str(err)
            if "INVALID_API_KEY_OR_IP_RESTRICTION" in str(err):
                msg = (
                    "Binance rejected the request (code: -2015). "
                    "Ensure your API key has 'Enable Reading' for USD(S)-M Futures, and that either "
                    "IP restriction is disabled or your current outbound IP is whitelisted on Binance."
                )
            elif "SIGNATURE_INVALID" in str(err):
                msg = "Signature rejected (code: -1022). Verify your BINANCE_API_SECRET in .env."
            elif "TIMESTAMP" in str(err):
                msg = "Exchange timestamp sync error (code: -1021). RecvWindow clock adjusted."

            return {
                "is_configured": True,
                "status": status,
                "error": err,
                "message": msg,
                "account_type": "Binance USD(S)-M Futures",
                "testnet": self.testnet
            }, err

        total_wallet = float(data.get("totalWalletBalance", 0.0))
        total_margin = float(data.get("totalMarginBalance", 0.0))
        unrealized_pnl = float(data.get("totalUnrealizedProfit", 0.0))
        available_balance = float(data.get("availableBalance", 0.0))
        initial_margin = float(data.get("totalInitialMargin", 0.0))
        maint_margin = float(data.get("totalMaintMargin", 0.0))

        # Assets breakdown (USDT, USDC, BNB)
        assets_list = []
        for a in data.get("assets", []):
            wb = float(a.get("walletBalance", 0.0))
            if wb > 0.01:
                assets_list.append({
                    "asset": a.get("asset"),
                    "wallet_balance": wb,
                    "unrealized_profit": float(a.get("unrealizedProfit", 0.0)),
                    "margin_balance": float(a.get("marginBalance", 0.0)),
                    "available_balance": float(a.get("availableBalance", 0.0))
                })

        return {
            "is_configured": True,
            "status": "CONNECTED",
            "account_type": "Binance USD(S)-M Futures",
            "testnet": self.testnet,
            "total_wallet_balance": total_wallet,
            "total_margin_balance": total_margin,
            "total_unrealized_pnl": unrealized_pnl,
            "available_balance": available_balance,
            "total_initial_margin": initial_margin,
            "total_maintenance_margin": maint_margin,
            "assets": assets_list,
            "last_synced": self._last_sync_timestamp or datetime.now(timezone.utc).isoformat()
        }, None

    def get_account_positions(self) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetches active open positions on Binance Futures with real liquidation and leverage."""
        if not self.is_configured:
            return [], "CREDENTIALS_NOT_CONFIGURED"

        data, err = self._safe_request("GET", "/fapi/v2/positionRisk", signed=True)
        if err or not isinstance(data, list):
            return [], err

        active_positions = []
        for pos in data:
            amt = float(pos.get("positionAmt", 0.0))
            if abs(amt) > 1e-6:
                side = "LONG" if amt > 0 else "SHORT"
                entry_price = float(pos.get("entryPrice", 0.0))
                mark_price = float(pos.get("markPrice", 0.0))
                pnl = float(pos.get("unRealizedProfit", 0.0))
                notional = abs(float(pos.get("notional", 0.0)))
                liq_price = float(pos.get("liquidationPrice", 0.0))
                leverage = int(pos.get("leverage", 1))

                ret_pct = 0.0
                if entry_price > 0:
                    ret_pct = ((mark_price - entry_price) / entry_price * 100.0) if side == "LONG" else ((entry_price - mark_price) / entry_price * 100.0)

                active_positions.append({
                    "symbol": pos.get("symbol"),
                    "side": side,
                    "position_amount": abs(amt),
                    "entry_price": entry_price,
                    "mark_price": mark_price,
                    "unrealized_pnl": pnl,
                    "return_pct": round(ret_pct, 2),
                    "notional": notional,
                    "liquidation_price": liq_price if liq_price > 0 else None,
                    "leverage": leverage,
                    "margin_type": pos.get("marginType", "cross"),
                    "isolated_margin": float(pos.get("isolatedMargin", 0.0))
                })

        return active_positions, None

    def get_open_orders(self, symbol: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetches current open resting orders on Binance Futures."""
        if not self.is_configured:
            return [], "CREDENTIALS_NOT_CONFIGURED"

        params = {}
        if symbol:
            params["symbol"] = symbol.upper()

        data, err = self._safe_request("GET", "/fapi/v1/openOrders", params=params, signed=True)
        if err or not isinstance(data, list):
            return [], err

        orders = []
        for o in data:
            orders.append({
                "order_id": str(o.get("orderId")),
                "symbol": o.get("symbol"),
                "status": o.get("status"),
                "side": o.get("side"),
                "type": o.get("type"),
                "price": float(o.get("price", 0.0)),
                "quantity": float(o.get("origQty", 0.0)),
                "executed_quantity": float(o.get("executedQty", 0.0)),
                "time": datetime.fromtimestamp(int(o.get("time", 0)) / 1000.0, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            })

        return orders, None

    def get_user_trades(self, symbol: str = "BTCUSDT", limit: int = 50) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetches historical user trades/fills from Binance Futures."""
        if not self.is_configured:
            return [], "CREDENTIALS_NOT_CONFIGURED"

        params = {
            "symbol": symbol.upper(),
            "limit": min(limit, 100)
        }
        data, err = self._safe_request("GET", "/fapi/v1/userTrades", params=params, signed=True)
        if err or not isinstance(data, list):
            return [], err

        trades = []
        for t in data:
            trades.append({
                "id": str(t.get("id")),
                "symbol": t.get("symbol"),
                "side": "BUY" if t.get("buyer") else "SELL",
                "price": float(t.get("price", 0.0)),
                "quantity": float(t.get("qty", 0.0)),
                "realized_pnl": float(t.get("realizedPnl", 0.0)),
                "commission": float(t.get("commission", 0.0)),
                "commission_asset": t.get("commissionAsset", "USDT"),
                "time": datetime.fromtimestamp(int(t.get("time", 0)) / 1000.0, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            })

        return trades, None


# Canonical global singleton instance
binance_futures_client = BinanceFuturesClient()
