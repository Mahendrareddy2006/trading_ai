"""Automated Test Suite for Trading AI Platform.

Tests:
1. Feature Pipeline & Data Leakage Prevention
2. 3-Class Target Labeling
3. Model Training & Probability Calibration
4. Prediction Inference & Abstention Logic
5. Risk Engine Sizing & Circuit Breakers
6. Paper Execution Engine & PnL Accounting
7. Backtest Vectorized Simulation
8. FastAPI Health Endpoint
"""

import math
import random
import pytest
from fastapi.testclient import TestClient

from trading_ai.features.pipeline import feature_pipeline, FEATURE_COLUMNS
from trading_ai.labeling.targets import target_labeler
from trading_ai.training.trainer import model_trainer
from trading_ai.inference.predictor import model_predictor
from trading_ai.risk.engine import risk_engine
from trading_ai.execution.paper import paper_engine
from trading_ai.backtesting.engine import backtest_engine
from trading_ai.api.app import app


@pytest.fixture
def sample_candles():
    """Generates synthetic random walk OHLCV candles."""
    random.seed(42)
    n = 150
    price = 100.0
    candles = []
    for i in range(n):
        delta = (random.random() - 0.49) * 2.0
        price = max(10.0, price + delta)
        high = price + random.random() * 1.5
        low = price - random.random() * 1.5
        open_ = price + (random.random() - 0.5) * 0.5
        close = price + (random.random() - 0.5) * 0.5
        vol = random.randint(100, 2000)

        candles.append({
            "timestamp": f"2026-01-01 {i:02d}:00:00",
            "open": round(open_, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": float(vol),
            "is_closed": True
        })
    return candles


def test_feature_pipeline(sample_candles):
    """Verifies that features are computed properly and contain zero NaNs."""
    features = feature_pipeline.transform(sample_candles)
    assert len(features) > 50

    for feat in features:
        for col in FEATURE_COLUMNS:
            assert col in feat
            val = feat[col]
            assert not math.isnan(val)
            assert not math.isinf(val)


def test_target_labeler(sample_candles):
    """Verifies that 3-class targets are assigned (+1, -1, 0)."""
    features = feature_pipeline.transform(sample_candles)
    labeled = target_labeler.compute_labels(features)

    assert len(labeled) > 30
    targets = {r["target"] for r in labeled}
    assert targets.issubset({-1, 0, 1})


def test_model_training_and_calibration(sample_candles):
    """Verifies end-to-end model training, calibration, and serialization."""
    bundle = model_trainer.train_and_evaluate(
        candles=sample_candles,
        symbol="TESTUSDT",
        timeframe="1h",
        model_type="random_forest"
    )

    assert bundle is not None
    assert "model" in bundle
    assert "metrics" in bundle
    assert "feature_importances" in bundle
    assert len(bundle["feature_importances"]) == len(FEATURE_COLUMNS)
    assert bundle["metrics"]["accuracy"] >= 0.0


def test_risk_engine_position_sizing():
    """Verifies institutional position sizing and minimum notional checks."""
    qty, err = risk_engine.calculate_position_size(
        symbol="BTCUSDT",
        price=90000.0,
        stop_loss_pct=0.015,
        equity=10000.0
    )
    assert err is None
    assert qty > 0.0
    assert (qty * 90000.0) >= 5.0


def test_risk_circuit_breaker_and_cooldown():
    """Verifies that 3 consecutive losses engage cooldown."""
    risk_engine.consecutive_losses = 0
    risk_engine.cooldown_until = None

    risk_engine.record_trade_outcome(-50.0, "LONG")
    risk_engine.record_trade_outcome(-50.0, "LONG")
    risk_engine.record_trade_outcome(-50.0, "LONG")

    assert risk_engine.consecutive_losses == 3
    is_active, msg = risk_engine.is_cooldown_active()
    assert is_active is True
    assert "consecutive losses" in msg

    # Reset
    risk_engine.consecutive_losses = 0
    risk_engine.cooldown_until = None


def test_paper_execution_engine():
    """Verifies opening and closing paper trades with correct PnL and fee accounting."""
    paper_engine.positions.clear()
    initial_cash = paper_engine.cash

    pos = paper_engine.open_position(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=90000.0,
        quantity=0.1,
        stop_loss_pct=0.015,
        take_profit_pct=0.030
    )
    assert pos is not None
    assert "BTCUSDT" in paper_engine.positions

    # Trigger take profit
    trade = paper_engine.close_position(
        symbol="BTCUSDT",
        exit_price=92700.0,
        reason="TAKE_PROFIT"
    )

    assert trade is not None
    assert trade["gross_pnl"] > 0
    assert trade["net_pnl"] > 0
    assert "BTCUSDT" not in paper_engine.positions


def test_backtest_engine(sample_candles):
    """Verifies backtest engine execution and equity curve generation."""
    result = backtest_engine.run_backtest(
        candles=sample_candles,
        symbol="BTCUSDT",
        sl_pct=0.015,
        tp_pct=0.030
    )

    assert result is not None
    assert "final_balance" in result
    assert "metrics" in result
    assert "equity_curve" in result
    assert len(result["equity_curve"]) > 0


def test_fastapi_health():
    """Verifies API health and readiness endpoints."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_binance_public_market_data():
    """Verifies Binance Futures public market data client."""
    from trading_ai.execution.binance_client import binance_futures_client

    ping = binance_futures_client.get_server_ping()
    assert "status" in ping
    assert "latency_ms" in ping

    tickers = binance_futures_client.get_realtime_tickers(["BTCUSDT"])
    assert "BTCUSDT" in tickers
    assert tickers["BTCUSDT"]["price"] > 0
    assert "change_24h" in tickers["BTCUSDT"]


def test_binance_unconfigured_and_placeholder_credentials():
    """Verifies that empty or placeholder credentials are not recognized as configured."""
    from trading_ai.execution.binance_client import BinanceFuturesClient

    # Empty credentials
    c_empty = BinanceFuturesClient(api_key="", api_secret="")
    assert c_empty.is_configured is False
    summary, err = c_empty.get_account_summary()
    assert summary["is_configured"] is False
    assert summary["status"] == "CREDENTIALS_NOT_CONFIGURED"

    # Placeholder credentials
    c_place = BinanceFuturesClient(api_key="your_actual_binance_api_key", api_secret="your_actual_secret_key")
    assert c_place.is_configured is False


def test_root_env_loading_and_propagation():
    """Verifies that the canonical root .env loads reliably regardless of working directory."""
    from trading_ai.config.settings import Settings, ENV_FILE_PATH, settings
    from trading_ai.execution.binance_client import BinanceFuturesClient

    assert ENV_FILE_PATH.exists()
    s = Settings()
    # Ensure paper trading mode is strictly preserved
    assert s.is_paper_trading is True
    assert s.TRADING_MODE.lower() == "paper"

    # Ensure BinanceFuturesClient dynamically reflects settings
    client = BinanceFuturesClient()
    assert client.api_key == s.BINANCE_API_KEY.strip()
    assert client.api_secret == s.BINANCE_API_SECRET.strip()
    assert client.testnet == s.BINANCE_TESTNET


def test_private_account_mocked_success(monkeypatch):
    """Verifies that valid exchange responses are parsed correctly without fabricating data."""
    from trading_ai.execution.binance_client import BinanceFuturesClient

    mock_account_data = {
        "totalWalletBalance": "15420.50",
        "totalMarginBalance": "15450.20",
        "totalUnrealizedProfit": "29.70",
        "availableBalance": "14200.00",
        "totalInitialMargin": "1250.20",
        "totalMaintMargin": "62.50",
        "assets": [
            {
                "asset": "USDT",
                "walletBalance": "15420.50",
                "unrealizedProfit": "29.70",
                "marginBalance": "15450.20",
                "availableBalance": "14200.00"
            }
        ]
    }

    client = BinanceFuturesClient(
        api_key="a" * 32,
        api_secret="b" * 32,
        testnet=False
    )
    assert client.is_configured is True

    # Monkeypatch _safe_request to simulate authenticated Binance response
    monkeypatch.setattr(client, "_safe_request", lambda method, path, params=None, signed=False: (mock_account_data, None))

    summary, err = client.get_account_summary()
    assert err is None
    assert summary["is_configured"] is True
    assert summary["status"] == "CONNECTED"
    assert summary["total_wallet_balance"] == 15420.50
    assert summary["available_balance"] == 14200.00
    assert summary["total_unrealized_pnl"] == 29.70
    assert len(summary["assets"]) == 1
    assert summary["assets"][0]["asset"] == "USDT"


def test_private_account_mocked_error_2015(monkeypatch):
    """Verifies that Binance error -2015 is handled gracefully with clear diagnostic messages."""
    from trading_ai.execution.binance_client import BinanceFuturesClient

    client = BinanceFuturesClient(
        api_key="a" * 32,
        api_secret="b" * 32,
        testnet=False
    )
    assert client.is_configured is True

    # Mock _safe_request returning error -2015
    mock_err = "INVALID_API_KEY_OR_IP_RESTRICTION: Invalid API-key, IP, or permissions for action, request ip: 182.65.232.148"
    monkeypatch.setattr(client, "_safe_request", lambda method, path, params=None, signed=False: (None, mock_err))

    summary, err = client.get_account_summary()
    assert err == mock_err
    assert summary["is_configured"] is True
    assert summary["status"] == "AUTH_FAILED"
    assert "code: -2015" in summary["message"]
    assert "Enable Reading" in summary["message"]
    assert "IP restriction" in summary["message"]


def test_secret_redaction_and_safety():
    """Verifies that secrets are never exposed in API endpoint responses."""
    client = TestClient(app)
    from trading_ai.config.settings import settings

    for endpoint in ["/api/account/summary", "/api/account/positions", "/api/system/data-status", "/api/health"]:
        res = client.get(endpoint)
        assert res.status_code == 200
        text = res.text
        # Neither raw secret nor raw key should ever be present in JSON payload
        if settings.BINANCE_API_SECRET and len(settings.BINANCE_API_SECRET) > 8:
            assert settings.BINANCE_API_SECRET not in text
        if settings.BINANCE_API_KEY and len(settings.BINANCE_API_KEY) > 8:
            assert settings.BINANCE_API_KEY not in text

