"""Automated Test Suite for Kraken Public Market Data Integration.

Verifies:
1. Public market data works with zero API keys, secrets, or exchange credentials.
2. Explicit quote currency differentiation: BTCUSDT (USDT) vs BTCUSD (USD), ARBUSD (USD).
3. Unsupported symbol handling (e.g. ARBUSDT) with clear quote-difference diagnostics.
4. Kraken market data provider parses ticker responses and OHLC candles accurately.
5. Populated ticker records: /api/market/tickers prevents empty responses.
6. Candle freshness evaluation: live vs stale detection based on timestamp age.
7. Upstream failure handling: stale cached data is flagged honestly and never disguised as live.
8. /api/system/data-status contract: Kraken provider, online status, credentials_required: False.
9. ML feature engineering and prediction compatibility on public candles.
10. Paper trading safety: live orders remain strictly disabled.
"""

from datetime import datetime, timezone, timedelta
import math
import pytest
from fastapi.testclient import TestClient

from trading_ai.api.app import app
from trading_ai.config.settings import settings
from trading_ai.data.providers.kraken import KrakenMarketDataProvider, SUPPORTED_KRAKEN_PAIRS
from trading_ai.data.providers.manager import CompositeMarketDataProvider, market_data_provider
from trading_ai.data.manager import data_manager
from trading_ai.execution.paper import PaperExecutionEngine
from trading_ai.features.pipeline import feature_pipeline, FEATURE_COLUMNS
from trading_ai.inference.predictor import model_predictor


@pytest.fixture
def client():
    return TestClient(app)


def test_public_provider_zero_credentials_requirement():
    """Verifies that the market data provider explicitly requires zero credentials."""
    provider = KrakenMarketDataProvider()
    assert provider.requires_credentials is False
    assert provider.name == "kraken"
    assert "Kraken" in provider.display_name


def test_kraken_symbol_mapping_and_quote_distinction():
    """Verifies explicit mapping of USDT and USD pairs and clear quote-currency separation."""
    provider = KrakenMarketDataProvider()

    # 1. USDT Pairs
    assert provider.map_symbol_to_kraken("BTCUSDT") == "XBTUSDT"
    info_btcusdt = provider.get_symbol_info("BTCUSDT")
    assert info_btcusdt is not None
    assert info_btcusdt.base_asset == "BTC"
    assert info_btcusdt.quote_asset == "USDT"

    assert provider.map_symbol_to_kraken("ETHUSDT") == "ETHUSDT"
    assert provider.get_symbol_info("ETHUSDT").quote_asset == "USDT"

    assert provider.map_symbol_to_kraken("SOLUSDT") == "SOLUSDT"
    assert provider.get_symbol_info("SOLUSDT").quote_asset == "USDT"

    assert provider.map_symbol_to_kraken("DOGEUSDT") == "XDGUSDT"
    assert provider.get_symbol_info("DOGEUSDT").quote_asset == "USDT"

    # 2. USD Pairs (Fiat USD)
    assert provider.map_symbol_to_kraken("BTCUSD") == "XXBTZUSD"
    info_btcusd = provider.get_symbol_info("BTCUSD")
    assert info_btcusd is not None
    assert info_btcusd.base_asset == "BTC"
    assert info_btcusd.quote_asset == "USD"

    assert provider.map_symbol_to_kraken("ARBUSD") == "ARBUSD"
    info_arbusd = provider.get_symbol_info("ARBUSD")
    assert info_arbusd is not None
    assert info_arbusd.base_asset == "ARB"
    assert info_arbusd.quote_asset == "USD"

    # 3. Reverse mapping
    assert provider.map_kraken_to_symbol("XBTUSDT") == "BTCUSDT"
    assert provider.map_kraken_to_symbol("XXBTZUSD") == "BTCUSD"
    assert provider.map_kraken_to_symbol("ARBUSD") == "ARBUSD"


def test_unsupported_symbol_handling_and_explanation():
    """Verifies unsupported symbols like ARBUSDT return honest explanation without substituting USD."""
    provider = KrakenMarketDataProvider()

    # ARBUSDT is not on Kraken spot (only ARBUSD is)
    assert provider.is_symbol_supported("ARBUSDT") is False
    explanation = provider.explain_unsupported_symbol("ARBUSDT")
    assert "ARBUSDT" in explanation
    assert "ARBUSD" in explanation
    assert "USDT" in explanation
    assert "USD" in explanation
    assert "Never silently substituting" in explanation


def test_kraken_timeframe_validation():
    """Verifies supported intervals and rejection of unsupported intervals."""
    provider = KrakenMarketDataProvider()

    assert provider.is_timeframe_supported("1m") is True
    assert provider.is_timeframe_supported("5m") is True
    assert provider.is_timeframe_supported("15m") is True
    assert provider.is_timeframe_supported("30m") is True
    assert provider.is_timeframe_supported("1h") is True
    assert provider.is_timeframe_supported("4h") is True
    assert provider.is_timeframe_supported("1d") is True

    # 3m is not natively supported by Kraken OHLC
    assert provider.is_timeframe_supported("3m") is False

    candles, err = provider.fetch_candles("BTCUSDT", "3m")
    assert candles == []
    assert err is not None
    assert "not supported" in err.lower()


def test_kraken_ticker_parsing_mocked(monkeypatch):
    """Verifies that official Kraken Ticker payload is parsed into standard TickerData structure."""
    provider = KrakenMarketDataProvider()

    mock_response = {
        "error": [],
        "result": {
            "XBTUSDT": {
                "a": ["65100.50000", "1", "1.000"],
                "b": ["65100.00000", "2", "2.000"],
                "c": ["65100.20000", "0.05000000"],
                "v": ["120.50", "350.25"],
                "p": ["64900.00", "64850.00"],
                "t": [1000, 3000],
                "l": ["64000.00", "63800.00"],
                "h": ["65500.00", "65600.00"],
                "o": "64000.00"
            }
        }
    }

    class MockResp:
        status_code = 200
        def json(self):
            return mock_response

    monkeypatch.setattr("requests.get", lambda url, params=None, timeout=None: MockResp())
    provider._ticker_cache.clear()
    provider._ticker_cache_time = 0.0

    tickers = provider.fetch_tickers(["BTCUSDT"])
    assert "BTCUSDT" in tickers
    t = tickers["BTCUSDT"]

    assert t["symbol"] == "BTCUSDT"
    assert t["base_asset"] == "BTC"
    assert t["quote_asset"] == "USDT"
    assert t["price"] == 65100.20
    # Kraken: 'a' is ask, 'b' is bid. Bid <= Ask in normal quote
    assert t["bid_price"] == 65100.00
    assert t["ask_price"] == 65100.50
    assert t["high_24h"] == 65600.00
    assert t["low_24h"] == 63800.00
    assert t["volume_24h"] == 350.25
    assert t["quote_volume_24h"] == round(350.25 * 64850.00, 2)
    assert t["spread"] == 0.50
    assert t["midpoint"] == 65100.25
    assert t["spread_pct"] == round(((65100.50 - 65100.00) / 65100.25) * 100.0, 4)
    assert t["quote_valid"] is True
    assert t["quote_error"] is None
    assert t["change_24h"] > 0
    assert t["data_source"] == "kraken_public"
    assert t["is_stale"] is False


def test_normal_quotes_spread_calculation_and_low_priced_precision(monkeypatch):
    """Verifies unrounded spread calculation and precision preservation for low-priced assets like ADA."""
    provider = KrakenMarketDataProvider()

    # ADA with micro-cent spread: bid = 0.254082, ask = 0.254083
    mock_ada = {
        "error": [],
        "result": {
            "ADAUSDT": {
                "a": ["0.254083", "5000", "5000.0"],
                "b": ["0.254082", "8000", "8000.0"],
                "c": ["0.2540825", "100.0"],
                "v": ["10000.0", "50000.0"],
                "p": ["0.25000", "0.25200"],
                "t": [100, 500],
                "l": ["0.24500", "0.24000"],
                "h": ["0.26000", "0.26500"],
                "o": "0.25000"
            }
        }
    }

    class MockResp:
        status_code = 200
        def json(self):
            return mock_ada

    monkeypatch.setattr("requests.get", lambda url, params=None, timeout=None: MockResp())
    provider._ticker_cache.clear()
    provider._ticker_cache_time = 0.0

    tickers = provider.fetch_tickers(["ADAUSDT"])
    assert "ADAUSDT" in tickers
    ada = tickers["ADAUSDT"]

    assert ada["bid_price"] == 0.254082
    assert ada["ask_price"] == 0.254083
    # Absolute spread must be exactly 0.000001 (not collapsed to 0 by premature rounding)
    assert ada["spread"] == 0.000001
    expected_midpoint = (0.254083 + 0.254082) / 2.0
    assert ada["midpoint"] == round(expected_midpoint, 8)
    expected_pct = ((0.254083 - 0.254082) / expected_midpoint) * 100.0
    assert ada["spread_pct"] == round(expected_pct, 4)
    assert ada["quote_valid"] is True
    assert ada["quote_error"] is None
    assert ada["is_stale"] is False


def test_crossed_quotes_detection_and_flagging(monkeypatch):
    """Verifies that crossed quotes (ask < bid) from upstream are flagged invalid and never silently swapped."""
    provider = KrakenMarketDataProvider()

    # Upstream anomaly: ask = 0.254082, bid = 0.254083
    mock_crossed = {
        "error": [],
        "result": {
            "ADAUSDT": {
                "a": ["0.254082", "5000", "5000.0"],
                "b": ["0.254083", "8000", "8000.0"],
                "c": ["0.254082", "100.0"],
                "v": ["10000.0", "50000.0"],
                "p": ["0.25000", "0.25200"],
                "t": [100, 500],
                "l": ["0.24500", "0.24000"],
                "h": ["0.26000", "0.26500"],
                "o": "0.25000"
            }
        }
    }

    class MockResp:
        status_code = 200
        def json(self):
            return mock_crossed

    monkeypatch.setattr("requests.get", lambda url, params=None, timeout=None: MockResp())
    provider._ticker_cache.clear()
    provider._ticker_cache_time = 0.0

    tickers = provider.fetch_tickers(["ADAUSDT"])
    ada = tickers["ADAUSDT"]

    # Must preserve actual reported values without fraudulent swapping
    assert ada["bid_price"] == 0.254083
    assert ada["ask_price"] == 0.254082
    # Must flag as invalid quote
    assert ada["quote_valid"] is False
    assert ada["quote_error"] is not None
    assert "Crossed quote" in ada["quote_error"]
    assert ada["data_freshness"] == "invalid_quote"
    assert ada["is_stale"] is True


def test_zero_and_negative_quotes_rejection(monkeypatch):
    """Verifies that non-positive or non-finite quote values are rejected and marked invalid."""
    provider = KrakenMarketDataProvider()

    # Zero bid price
    mock_zero = {
        "error": [],
        "result": {
            "BTCUSDT": {
                "a": ["65000.0", "1", "1"],
                "b": ["0.0", "1", "1"],
                "c": ["65000.0", "1"],
                "v": ["10", "20"],
                "p": ["65000", "65000"],
                "t": [1, 2],
                "l": ["64000", "64000"],
                "h": ["66000", "66000"],
                "o": "65000"
            }
        }
    }

    class MockResp:
        status_code = 200
        def json(self):
            return mock_zero

    monkeypatch.setattr("requests.get", lambda url, params=None, timeout=None: MockResp())
    provider._ticker_cache.clear()
    provider._ticker_cache_time = 0.0

    tickers = provider.fetch_tickers(["BTCUSDT"])
    btc = tickers["BTCUSDT"]

    assert btc["quote_valid"] is False
    assert btc["quote_error"] is not None
    assert "Non-positive" in btc["quote_error"]
    assert btc["is_stale"] is True


def test_malformed_kraken_payload_handling(monkeypatch):
    """Verifies that malformed payloads with missing fields or corrupt arrays do not crash."""
    provider = KrakenMarketDataProvider()

    mock_malformed = {
        "error": [],
        "result": {
            "BTCUSDT": {
                "c": ["65000.0", "1"]
                # Missing 'a', 'b', 'h', 'l', etc.
            }
        }
    }

    class MockResp:
        status_code = 200
        def json(self):
            return mock_malformed

    monkeypatch.setattr("requests.get", lambda url, params=None, timeout=None: MockResp())
    provider._ticker_cache.clear()
    provider._ticker_cache_time = 0.0

    tickers = provider.fetch_tickers(["BTCUSDT"])
    btc = tickers["BTCUSDT"]

    assert btc["quote_valid"] is False
    assert btc["quote_error"] is not None
    assert "Malformed" in btc["quote_error"]
    assert btc["data_freshness"] == "malformed_quote"
    assert btc["is_stale"] is True


def test_usdt_versus_usd_pairs_ticker_parsing(monkeypatch):
    """Verifies distinct parsing and quote currency isolation between USDT and USD pairs."""
    provider = KrakenMarketDataProvider()

    mock_pairs = {
        "error": [],
        "result": {
            "XBTUSDT": {
                "a": ["65100.5", "1", "1"],
                "b": ["65100.0", "1", "1"],
                "c": ["65100.2", "1"],
                "v": ["10", "20"],
                "p": ["65000", "65000"],
                "t": [1, 2],
                "l": ["64000", "64000"],
                "h": ["66000", "66000"],
                "o": "65000"
            },
            "XXBTZUSD": {
                "a": ["65080.5", "2", "2"],
                "b": ["65080.0", "2", "2"],
                "c": ["65080.2", "1"],
                "v": ["15", "30"],
                "p": ["65050", "65050"],
                "t": [5, 10],
                "l": ["64000", "64000"],
                "h": ["66000", "66000"],
                "o": "65000"
            }
        }
    }

    class MockResp:
        status_code = 200
        def json(self):
            return mock_pairs

    monkeypatch.setattr("requests.get", lambda url, params=None, timeout=None: MockResp())
    provider._ticker_cache.clear()
    provider._ticker_cache_time = 0.0

    tickers = provider.fetch_tickers(["BTCUSDT", "BTCUSD"])
    assert "BTCUSDT" in tickers
    assert "BTCUSD" in tickers

    btc_usdt = tickers["BTCUSDT"]
    btc_usd = tickers["BTCUSD"]

    assert btc_usdt["quote_asset"] == "USDT"
    assert btc_usdt["ask_price"] == 65100.5
    assert btc_usdt["bid_price"] == 65100.0

    assert btc_usd["quote_asset"] == "USD"
    assert btc_usd["ask_price"] == 65080.5
    assert btc_usd["bid_price"] == 65080.0


def test_paper_engine_rejects_invalid_and_crossed_quotes():
    """Verifies that the paper-trading engine refuses to open or close simulated positions on invalid quotes."""
    engine = PaperExecutionEngine()

    # 1. Rejects open_position when quote_valid is False
    res_invalid = engine.open_position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=65000.0,
        quantity=0.1,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        bid_price=64990.0,
        ask_price=65010.0,
        quote_valid=False
    )
    assert res_invalid is None
    assert "BTCUSDT" not in engine.positions

    # 2. Rejects open_position on crossed quotes (ask < bid)
    res_crossed = engine.open_position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=65000.0,
        quantity=0.1,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        bid_price=65100.0,
        ask_price=65000.0,
        quote_valid=True
    )
    assert res_crossed is None
    assert "BTCUSDT" not in engine.positions

    # 3. Rejects open_position on non-positive or non-finite quotes
    res_zero = engine.open_position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=65000.0,
        quantity=0.1,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        bid_price=0.0,
        ask_price=65000.0,
        quote_valid=True
    )
    assert res_zero is None
    assert "BTCUSDT" not in engine.positions

    # 4. Successfully opens position on valid quotes and uses ask for LONG
    res_valid_long = engine.open_position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=65000.0,
        quantity=0.1,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        bid_price=64990.0,
        ask_price=65010.0,
        quote_valid=True
    )
    assert res_valid_long is not None
    assert "BTCUSDT" in engine.positions
    # LONG executed at ask * (1 + slippage)
    expected_fill = 65010.0 * (1 + engine.slippage_pct)
    assert abs(res_valid_long["entry_price"] - expected_fill) < 1e-4

    # 5. Rejects close_position when quote_valid is False
    res_close_invalid = engine.close_position(
        symbol="BTCUSDT",
        exit_price=66000.0,
        quote_valid=False
    )
    assert res_close_invalid is None
    assert "BTCUSDT" in engine.positions

    # 6. Rejects close_position on crossed quotes
    res_close_crossed = engine.close_position(
        symbol="BTCUSDT",
        exit_price=66000.0,
        bid_price=66100.0,
        ask_price=66000.0,
        quote_valid=True
    )
    assert res_close_crossed is None
    assert "BTCUSDT" in engine.positions

    # 7. Successfully closes on valid quotes (closing LONG sells at bid)
    res_close_valid = engine.close_position(
        symbol="BTCUSDT",
        exit_price=66000.0,
        bid_price=66000.0,
        ask_price=66010.0,
        quote_valid=True
    )
    assert res_close_valid is not None
    assert "BTCUSDT" not in engine.positions
    expected_exit = 66000.0 * (1 - engine.slippage_pct)
    assert abs(res_close_valid["exit_price"] - expected_exit) < 1e-4

    # 8. on_price_update returns None when quote_valid is False
    assert engine.on_price_update("BTCUSDT", 66000.0, quote_valid=False) is None



def test_kraken_candle_parsing_and_limit_slicing(monkeypatch):
    """Verifies that Kraken OHLC payload is parsed into validated OHLCV dictionaries and respects limit."""
    provider = KrakenMarketDataProvider()

    mock_ohlc = {
        "error": [],
        "result": {
            "XBTUSDT": [
                [1700000000, "60000.0", "60500.0", "59800.0", "60200.0", "60100.0", "12.50", 120],
                [1700003600, "60200.0", "61000.0", "60150.0", "60800.0", "60600.0", "15.75", 150],
                [1700007200, "60800.0", "61200.0", "60700.0", "61100.0", "60900.0", "18.20", 180],
            ],
            "last": 1700007200
        }
    }

    class MockResp:
        status_code = 200
        def json(self):
            return mock_ohlc

    monkeypatch.setattr("requests.get", lambda url, params=None, timeout=None: MockResp())

    # Limit = 2
    candles, err = provider.fetch_candles("BTCUSDT", "1h", limit=2)
    assert err is None
    assert len(candles) == 2

    c0 = candles[0]
    assert c0["open"] == 60200.0
    assert c0["high"] == 61000.0
    assert c0["low"] == 60150.0
    assert c0["close"] == 60800.0
    assert c0["volume"] == 15.75
    assert c0["is_closed"] is True


def test_candle_freshness_logic():
    """Verifies that recent timestamps are marked live and ancient timestamps are marked stale."""
    now_utc = datetime.now(timezone.utc)

    # 1. Fresh timestamp (10 minutes ago)
    fresh_ts = (now_utc - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    assert data_manager.is_candle_fresh(fresh_ts, "1h") is True

    # 2. Stale timestamp (from February 27, 2026)
    stale_ts = "2026-02-27 23:00:00"
    assert data_manager.is_candle_fresh(stale_ts, "1h") is False


def test_stale_cache_not_treated_as_live(monkeypatch):
    """Verifies that when upstream fails, old cached data is returned with is_stale=True."""
    # Force provider to fail
    monkeypatch.setattr(data_manager.provider, "fetch_candles", lambda sym, tf, limit=100: ([], "Simulated upstream timeout"))

    # Mock load_candles returning old February 2026 candles
    old_candles = [
        {"timestamp": "2026-02-27 22:00:00", "open": 64000.0, "high": 64200.0, "low": 63900.0, "close": 64100.0, "volume": 10.0, "is_closed": True},
        {"timestamp": "2026-02-27 23:00:00", "open": 64100.0, "high": 64300.0, "low": 64000.0, "close": 64200.0, "volume": 12.0, "is_closed": True}
    ]
    monkeypatch.setattr(data_manager, "load_candles", lambda sym, tf: old_candles)

    detailed = data_manager.get_candles_detailed("BTCUSDT", "1h", limit=5)
    assert detailed["is_stale"] is True
    assert detailed["data_freshness"] == "stale"
    assert detailed["data_source"] == "cached_local"
    assert "stale" in detailed["warning"].lower()
    assert len(detailed["candles"]) == 2


def test_empty_tickers_prevention():
    """Verifies that fetch_realtime_tickers returns populated records for all default symbols."""
    tickers = data_manager.fetch_realtime_tickers(settings.default_symbols)
    assert len(tickers) > 0
    for sym in settings.default_symbols:
        assert sym in tickers
        t = tickers[sym]
        assert "price" in t
        assert t["price"] > 0
        assert "spread" in t
        assert "timestamp" in t


def test_api_system_data_status_contract(client):
    """Verifies that /api/system/data-status accurately reports Kraken and requires zero credentials."""
    res = client.get("/api/system/data-status")
    assert res.status_code == 200
    data = res.json()

    assert data["public_data_source"] == "kraken"
    assert data["public_data_active"] is True
    assert data["credentials_required"] is False
    assert data["credentials_configured"] is False
    assert data["is_paper_trading"] is True
    assert "last_successful_update" in data

    conn = data["exchange_connectivity"]
    assert "Kraken" in conn["exchange"]
    assert conn["provider"] == "kraken"
    assert conn["endpoint"] == "https://api.kraken.com/0/public"
    assert conn["credentials_required"] is False
    assert conn["status"] in ["online", "degraded"]


def test_api_market_tickers_contract(client):
    """Verifies that /api/market/tickers returns populated records and metadata."""
    res = client.get("/api/market/tickers")
    assert res.status_code == 200
    data = res.json()

    assert "tickers" in data
    assert data["count"] > 0
    assert "BTCUSDT" in data["tickers"]
    btc = data["tickers"]["BTCUSDT"]
    assert btc["price"] > 0
    assert btc["data_source"] == "kraken_public"


def test_api_market_candles_live_and_unsupported(client):
    """Verifies /api/market/candles returns live data for supported pairs and 400 for unsupported pairs."""
    # 1. Supported pair BTCUSDT
    res_btc = client.get("/api/market/candles?symbol=BTCUSDT&timeframe=1h&limit=5")
    assert res_btc.status_code == 200
    btc_data = res_btc.json()
    assert btc_data["symbol"] == "BTCUSDT"
    assert btc_data["quote_asset"] == "USDT"
    assert len(btc_data["candles"]) > 0

    # 2. Supported USD pair ARBUSD
    res_arb = client.get("/api/market/candles?symbol=ARBUSD&timeframe=1h&limit=5")
    assert res_arb.status_code == 200
    arb_data = res_arb.json()
    assert arb_data["symbol"] == "ARBUSD"
    assert arb_data["quote_asset"] == "USD"
    assert len(arb_data["candles"]) > 0

    # 3. Unsupported pair ARBUSDT returns 400 with helpful explanation
    res_arbusdt = client.get("/api/market/candles?symbol=ARBUSDT&timeframe=1h&limit=5")
    assert res_arbusdt.status_code == 400
    detail = res_arbusdt.json().get("detail", "")
    assert "ARBUSDT" in detail
    assert "ARBUSD" in detail
    assert "Never silently substituting" in detail


def test_feature_pipeline_compatibility():
    """Verifies public candle data is compatible with ML feature engineering."""
    candles = []
    base_price = 60000.0
    for i in range(100):
        candles.append({
            "timestamp": f"2026-01-01 {i:02d}:00:00",
            "open": base_price + i * 2.0,
            "high": base_price + i * 2.0 + 15.0,
            "low": base_price + i * 2.0 - 15.0,
            "close": base_price + i * 2.0 + 5.0,
            "volume": 10.0 + (i % 5),
            "is_closed": True
        })

    features = feature_pipeline.transform(candles)
    assert len(features) > 30

    for feat in features:
        for col in FEATURE_COLUMNS:
            assert col in feat
            val = feat[col]
            assert not math.isnan(val)
            assert not math.isinf(val)


def test_model_inference_on_public_candles():
    """Verifies model predictor works on public candle format."""
    candles = []
    base_price = 80000.0
    for i in range(120):
        candles.append({
            "timestamp": f"2026-02-01 {i:02d}:00:00",
            "open": base_price + (i % 10) * 10,
            "high": base_price + (i % 10) * 10 + 20,
            "low": base_price + (i % 10) * 10 - 20,
            "close": base_price + (i % 10) * 10 + 5,
            "volume": 50.0,
            "is_closed": True
        })

    pred = model_predictor.predict(candles, "BTCUSDT", "1h")
    assert pred is not None
    p_dict = pred.to_dict()
    assert p_dict["symbol"] == "BTCUSDT"
    assert p_dict["direction"] in ["LONG", "SHORT", "NEUTRAL"]
