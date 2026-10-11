"""SQLAlchemy models for persistence.

Stores candles, predictions, training jobs, registered models,
orders, positions, closed trades, backtest runs, and risk audit logs.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, Index, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Candle(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    is_closed = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_candle_sym_tf_time", "symbol", "timeframe", "timestamp", unique=True),
    )


class PredictionRecord(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now, index=True)
    model_version = Column(String(50), nullable=False)
    predicted_class = Column(Integer, nullable=False)  # 1 (BUY), -1 (SELL), 0 (NEUTRAL)
    up_prob = Column(Float, nullable=False)
    down_prob = Column(Float, nullable=False)
    neutral_prob = Column(Float, default=0.0)
    edge = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    regime = Column(String(20), default="NEUTRAL")
    abstention_reason = Column(String(100), nullable=True)


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(String(64), primary_key=True)
    job_name = Column(String(100), nullable=False)
    status = Column(String(20), default="PENDING", index=True)  # PENDING, RUNNING, COMPLETED, FAILED
    config_json = Column(Text, default="{}")
    metrics_json = Column(Text, default="{}")
    logs = Column(Text, default="")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ModelRecord(Base):
    __tablename__ = "model_records"

    id = Column(String(64), primary_key=True)
    model_name = Column(String(100), nullable=False)
    model_type = Column(String(50), nullable=False)  # random_forest, logistic_regression, gradient_boost
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    metrics_json = Column(Text, default="{}")
    file_path = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class OrderRecord(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), unique=True, index=True, nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY, SELL
    order_type = Column(String(30), nullable=False)  # LIMIT, MARKET, STOP_MARKET, TAKE_PROFIT_MARKET
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    status = Column(String(20), default="NEW", index=True)  # NEW, FILLED, CANCELED, REJECTED
    fill_price = Column(Float, nullable=True)
    fee = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now)


class PositionRecord(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    side = Column(String(10), nullable=False)  # LONG, SHORT
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    leverage = Column(Integer, default=1)
    unrealized_pnl = Column(Float, default=0.0)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    status = Column(String(20), default="OPEN", index=True)  # OPEN, CLOSED
    opened_at = Column(DateTime(timezone=True), default=utc_now)
    closed_at = Column(DateTime(timezone=True), nullable=True)


class TradeRecord(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(64), unique=True, index=True, nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # LONG, SHORT
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    leverage = Column(Integer, default=1)
    gross_pnl = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    net_pnl = Column(Float, nullable=False)
    return_pct = Column(Float, nullable=False)
    exit_reason = Column(String(30), default="TARGET")  # TAKE_PROFIT, STOP_LOSS, MANUAL, KILL_SWITCH
    strategy_name = Column(String(50), default="ML_Strategy")
    model_version = Column(String(50), default="v1.0")
    opened_at = Column(DateTime(timezone=True), default=utc_now)
    closed_at = Column(DateTime(timezone=True), default=utc_now)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(String(64), primary_key=True)
    name = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    start_date = Column(String(30), nullable=False)
    end_date = Column(String(30), nullable=False)
    initial_balance = Column(Float, default=10000.0)
    final_balance = Column(Float, default=10000.0)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    equity_curve_json = Column(Text, default="[]")
    trades_json = Column(Text, default="[]")
    params_json = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=utc_now)


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default="WARNING")  # INFO, WARNING, CRITICAL
    details = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utc_now)


# ============================================================================
# Multi-User Authentication & Exchange Credential Isolation Models
# ============================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)  # UUID
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    credentials = relationship("ExchangeCredential", back_populates="user", cascade="all, delete-orphan")
    watchlists = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")


class ExchangeCredential(Base):
    __tablename__ = "exchange_credentials"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exchange = Column(String(30), default="binance_futures", nullable=False)
    label = Column(String(50), default="Binance USD(S)-M Futures", nullable=False)
    encrypted_api_key = Column(Text, nullable=False)
    encrypted_api_secret = Column(Text, nullable=False)
    key_mask = Column(String(20), nullable=False)  # e.g., "abcd****1234"
    testnet = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    status = Column(String(30), default="NOT_CONNECTED")  # NOT_CONNECTED, VALIDATING, CONNECTED, AUTH_FAILED
    last_error = Column(Text, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="credentials")


class UserWatchlist(Base):
    __tablename__ = "user_watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        Index("idx_user_symbol_watchlist", "user_id", "symbol", unique=True),
    )

    user = relationship("User", back_populates="watchlists")
