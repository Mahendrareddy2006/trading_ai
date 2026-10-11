"""SQLAlchemy models for persistence.

Stores candles, predictions, training jobs, registered models,
orders, positions, closed trades, backtest runs, and risk audit logs.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, Index, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return str(uuid.uuid4())


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
    notification_settings = relationship("NotificationSetting", back_populates="user", uselist=False, cascade="all, delete-orphan")
    price_rules = relationship("PriceAlertRule", back_populates="user", cascade="all, delete-orphan")
    in_app_notifications = relationship("InAppNotification", back_populates="user", cascade="all, delete-orphan")
    delivery_logs = relationship("NotificationDeliveryLog", back_populates="user", cascade="all, delete-orphan")


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


# ============================================================================
# Notification Center & Alert Engine Models
# ============================================================================

class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    id = Column(String(36), primary_key=True, default=gen_uuid)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Channels
    telegram_enabled = Column(Boolean, default=False)
    telegram_bot_token = Column(Text, nullable=True)  # Optional per-user bot token override
    telegram_chat_id = Column(String(64), nullable=True)
    telegram_verified = Column(Boolean, default=False)
    telegram_status = Column(String(30), default="NOT_CONFIGURED")  # NOT_CONFIGURED, VALIDATING, CONNECTED, INVALID_CREDENTIALS, CONFIGURATION_ERROR, PROVIDER_UNAVAILABLE
    telegram_verified_at = Column(DateTime(timezone=True), nullable=True)
    telegram_sender_info = Column(String(100), nullable=True)  # e.g. "@trading_ai_bot"
    telegram_last_delivery = Column(DateTime(timezone=True), nullable=True)
    telegram_last_error = Column(Text, nullable=True)

    whatsapp_enabled = Column(Boolean, default=False)
    whatsapp_provider = Column(String(30), default="meta")
    whatsapp_api_token = Column(Text, nullable=True)  # Optional per-user or tenant Meta token
    whatsapp_phone_number_id = Column(String(64), nullable=True)  # Meta Business Sender Phone Number ID
    whatsapp_phone_number = Column(String(32), nullable=True)  # Recipient E.164 phone number (e.g. +14155552671)
    whatsapp_verified = Column(Boolean, default=False)
    whatsapp_status = Column(String(30), default="NOT_CONFIGURED")  # NOT_CONFIGURED, VALIDATING, CONNECTED, INVALID_CREDENTIALS, CONFIGURATION_ERROR, PROVIDER_UNAVAILABLE
    whatsapp_verified_at = Column(DateTime(timezone=True), nullable=True)
    whatsapp_sender_info = Column(String(100), nullable=True)  # e.g. "+1 555-0199 (Verified: My Trading)"
    whatsapp_last_delivery = Column(DateTime(timezone=True), nullable=True)
    whatsapp_last_error = Column(Text, nullable=True)

    in_app_enabled = Column(Boolean, default=True)

    # Coin Selection (Applies to all website-supported coins or custom subset)
    all_coins = Column(Boolean, default=True)
    selected_coins_json = Column(Text, default="[]")  # JSON array of symbols, e.g. ["BTCUSDT", "ETHUSDT"]

    # ML Signal Alert Filters
    ml_alerts_enabled = Column(Boolean, default=True)
    ml_min_confidence = Column(Float, default=70.0)  # User threshold: 0.0 to 100.0% (e.g. 70.0 = 70%)
    ml_min_edge = Column(Float, default=2.0)
    ml_notify_buy = Column(Boolean, default=True)
    ml_notify_sell = Column(Boolean, default=True)
    ml_notify_neutral = Column(Boolean, default=False)
    ml_timeframes = Column(String(50), default="1h,5m")

    # Market News Alert Filters
    news_alerts_enabled = Column(Boolean, default=True)
    news_categories_json = Column(Text, default='["all","bitcoin","ethereum","altcoins","regulation","macro","exchanges","defi"]')

    # Risk and System Alerts
    risk_alerts_enabled = Column(Boolean, default=True)
    notify_circuit_breaker = Column(Boolean, default=True)
    notify_daily_loss = Column(Boolean, default=True)
    notify_drawdown = Column(Boolean, default=True)
    notify_consecutive_losses = Column(Boolean, default=True)
    notify_service_health = Column(Boolean, default=True)

    # Delivery Mode & Scheduled Summaries
    delivery_mode = Column(String(20), default="instant")  # "instant", "summary", "both"
    summary_frequency = Column(String(20), default="daily")  # "hourly", "daily", "weekly"
    summary_time = Column(String(10), default="09:00")  # UTC time, e.g. "09:00"
    summary_timezone = Column(String(50), default="UTC")
    last_summary_sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="notification_settings")


class PriceAlertRule(Base):
    __tablename__ = "price_alert_rules"

    id = Column(String(36), primary_key=True, default=gen_uuid)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    
    # Boundary Conditions
    condition_type = Column(String(30), nullable=False)  # "entering_range", "exiting_range", "crossing_up", "crossing_down"
    lower_boundary = Column(Float, nullable=True)
    upper_boundary = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)  # Used for single price crossing
    
    # Delivery Channels for this rule
    channels = Column(String(50), default="in_app,telegram")  # comma-separated: in_app,telegram,whatsapp
    is_active = Column(Boolean, default=True)
    
    # Evaluation state tracking
    last_evaluated_price = Column(Float, nullable=True)
    last_state = Column(String(20), nullable=True)  # "INSIDE", "OUTSIDE", "ABOVE", "BELOW"
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    cooldown_seconds = Column(Integer, default=300)  # 5 min cooldown to prevent tick spam
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="price_rules")


class InAppNotification(Base):
    __tablename__ = "in_app_notifications"

    id = Column(String(36), primary_key=True, default=gen_uuid)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(30), nullable=False, index=True)  # "ml_signal", "price_alert", "market_news", "risk_event", "system"
    severity = Column(String(20), default="info")  # "info", "success", "warning", "critical"
    symbol = Column(String(20), nullable=True, index=True)
    metadata_json = Column(Text, default="{}")  # Stored price, url, confidence, etc.
    is_read = Column(Boolean, default=False, index=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    user = relationship("User", back_populates="in_app_notifications")


class NotificationDeliveryLog(Base):
    __tablename__ = "notification_delivery_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(20), nullable=False, index=True)  # "telegram", "whatsapp", "in_app"
    category = Column(String(30), nullable=False)
    status = Column(String(20), default="PENDING", index=True)  # "DELIVERED", "FAILED", "SKIPPED"
    recipient = Column(String(100), nullable=False)  # Masked chat ID, phone, or user_id
    error_message = Column(Text, nullable=True)
    payload_preview = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    user = relationship("User", back_populates="delivery_logs")
