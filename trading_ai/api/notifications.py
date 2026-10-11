"""Notification Center REST API Router.

Provides authenticated user endpoints for:
- Reading and updating notification channel settings (Telegram, WhatsApp, In-App)
- Coin selection & ML confidence threshold configuration
- Price-range and price-crossing rule management
- In-app notification listing, unread count, and read status updates
- Test notification dispatch and delivery history logs
"""

from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from trading_ai.api.deps import get_current_user, get_optional_current_user
from trading_ai.config.settings import settings
from trading_ai.core.env_manager import (
    is_cloud_environment,
    is_env_file_writable,
    get_deployment_context,
    update_whitelisted_env_keys
)
from trading_ai.database.models import (
    User,
    NotificationSetting,
    PriceAlertRule,
    InAppNotification,
    NotificationDeliveryLog,
    utc_now
)
from trading_ai.database.session import get_db
from trading_ai.services.notification_service import notification_service

notification_router = APIRouter(prefix="/api/notifications", tags=["Notification Center"])

E164_REGEX = re.compile(r"^\+[1-9]\d{6,14}$")


# ============================================================================
# Schemas
# ============================================================================

class NotificationSettingsResponse(BaseModel):
    user_id: str
    telegram_enabled: bool
    telegram_status: str
    telegram_chat_id_masked: Optional[str] = None
    telegram_has_custom_token: bool
    telegram_verified: bool
    telegram_verified_at: Optional[str] = None
    telegram_sender_info: Optional[str] = None
    telegram_last_delivery: Optional[str] = None
    telegram_last_error: Optional[str] = None
    server_telegram_configured: bool

    whatsapp_enabled: bool
    whatsapp_status: str
    whatsapp_phone_number_masked: Optional[str] = None
    whatsapp_phone_number_id_masked: Optional[str] = None
    whatsapp_verified: bool
    whatsapp_verified_at: Optional[str] = None
    whatsapp_sender_info: Optional[str] = None
    whatsapp_last_delivery: Optional[str] = None
    whatsapp_last_error: Optional[str] = None
    server_whatsapp_configured: bool
    whatsapp_provider: str

    in_app_enabled: bool
    in_app_status: str
    in_app_verified_at: Optional[str] = None

    all_coins: bool
    selected_coins: List[str]
    available_symbols: List[str]

    ml_alerts_enabled: bool
    ml_min_confidence: float
    ml_min_edge: float
    ml_notify_buy: bool
    ml_notify_sell: bool
    ml_notify_neutral: bool
    ml_timeframes: List[str]

    news_alerts_enabled: bool
    news_categories: List[str]

    risk_alerts_enabled: bool
    notify_circuit_breaker: bool
    notify_daily_loss: bool
    notify_drawdown: bool
    notify_consecutive_losses: bool
    notify_service_health: bool

    delivery_mode: str
    summary_frequency: str
    summary_time: str
    summary_timezone: str
    last_summary_sent_at: Optional[str] = None

    env_writable: bool
    is_cloud: bool
    platform: str


class ConfigureWhatsAppRequest(BaseModel):
    api_token: str = Field(..., min_length=10, description="Meta WhatsApp Cloud API Access Token")
    phone_number_id: str = Field(..., min_length=5, description="Meta WhatsApp Phone Number ID")
    recipient_phone: Optional[str] = Field(None, description="E.164 formatted recipient phone number")
    provider: Optional[str] = "meta"
    save_to_local_env: Optional[bool] = True


class ConfigureTelegramRequest(BaseModel):
    bot_token: str = Field(..., min_length=10, description="Telegram Bot Token from @BotFather")
    chat_id: Optional[str] = Field(None, description="Telegram recipient User ID or Channel ID")
    save_to_local_env: Optional[bool] = True


class UpdateNotificationSettingsRequest(BaseModel):
    telegram_enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    whatsapp_enabled: Optional[bool] = None
    whatsapp_phone_number: Optional[str] = None

    in_app_enabled: Optional[bool] = None

    all_coins: Optional[bool] = None
    selected_coins: Optional[List[str]] = None

    ml_alerts_enabled: Optional[bool] = None
    ml_min_confidence: Optional[float] = Field(None, ge=0.0, le=100.0)
    ml_min_edge: Optional[float] = Field(None, ge=0.0, le=100.0)
    ml_notify_buy: Optional[bool] = None
    ml_notify_sell: Optional[bool] = None
    ml_notify_neutral: Optional[bool] = None
    ml_timeframes: Optional[List[str]] = None

    news_alerts_enabled: Optional[bool] = None
    news_categories: Optional[List[str]] = None

    risk_alerts_enabled: Optional[bool] = None
    notify_circuit_breaker: Optional[bool] = None
    notify_daily_loss: Optional[bool] = None
    notify_drawdown: Optional[bool] = None
    notify_consecutive_losses: Optional[bool] = None
    notify_service_health: Optional[bool] = None

    delivery_mode: Optional[str] = None
    summary_frequency: Optional[str] = None
    summary_time: Optional[str] = None
    summary_timezone: Optional[str] = None


class TestNotificationRequest(BaseModel):
    token_override: Optional[str] = None
    chat_id_override: Optional[str] = None
    phone_override: Optional[str] = None


class PriceAlertRuleCreate(BaseModel):
    symbol: str
    condition_type: str  # entering_range, exiting_range, crossing_up, crossing_down
    lower_boundary: Optional[float] = None
    upper_boundary: Optional[float] = None
    target_price: Optional[float] = None
    channels: Optional[str] = "in_app,telegram"
    cooldown_seconds: Optional[int] = 300


class PriceAlertRuleResponse(BaseModel):
    id: str
    user_id: str
    symbol: str
    condition_type: str
    lower_boundary: Optional[float] = None
    upper_boundary: Optional[float] = None
    target_price: Optional[float] = None
    channels: str
    is_active: bool
    last_evaluated_price: Optional[float] = None
    last_state: Optional[str] = None
    last_triggered_at: Optional[str] = None
    cooldown_seconds: int
    created_at: str


class InAppNotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    category: str
    severity: str
    symbol: Optional[str] = None
    metadata: Dict[str, Any]
    is_read: bool
    created_at: str


def _mask_value(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    val = val.strip()
    if len(val) <= 4:
        return "****"
    return val[:2] + "****" + val[-2:]


# ============================================================================
# Endpoints
# ============================================================================

@notification_router.get("/settings", response_model=NotificationSettingsResponse)
def get_notification_settings(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves the notification settings for the authenticated user with masked secrets."""
    user_id = current_user.id if current_user else "sandbox_default"
    s = notification_service.get_or_create_settings(db, user_id)

    selected_coins = []
    if s.selected_coins_json:
        try:
            selected_coins = json.loads(s.selected_coins_json)
        except Exception:
            selected_coins = settings.default_symbols

    news_categories = []
    if s.news_categories_json:
        try:
            news_categories = json.loads(s.news_categories_json)
        except Exception:
            news_categories = ["all"]

    tf_list = [t.strip() for t in (s.ml_timeframes or "1h,5m").split(",") if t.strip()]

    server_tg = bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_ENABLED)
    server_wa = bool(settings.WHATSAPP_API_TOKEN and settings.WHATSAPP_ENABLED)

    dep_ctx = get_deployment_context()

    # Determine backend-derived statuses
    tg_status = s.telegram_status or ("CONNECTED" if s.telegram_verified else "NOT_CONFIGURED")
    wa_status = s.whatsapp_status or ("CONNECTED" if s.whatsapp_verified else "NOT_CONFIGURED")
    in_app_status = "CONNECTED" if s.in_app_enabled else "NOT_CONFIGURED"

    wa_phone_id = s.whatsapp_phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID

    return NotificationSettingsResponse(
        user_id=user_id,
        telegram_enabled=s.telegram_enabled,
        telegram_status=tg_status,
        telegram_chat_id_masked=_mask_value(s.telegram_chat_id),
        telegram_has_custom_token=bool(s.telegram_bot_token),
        telegram_verified=s.telegram_verified,
        telegram_verified_at=s.telegram_verified_at.isoformat() if s.telegram_verified_at else None,
        telegram_sender_info=s.telegram_sender_info,
        telegram_last_delivery=s.telegram_last_delivery.isoformat() if s.telegram_last_delivery else None,
        telegram_last_error=s.telegram_last_error,
        server_telegram_configured=server_tg,

        whatsapp_enabled=s.whatsapp_enabled,
        whatsapp_status=wa_status,
        whatsapp_phone_number_masked=_mask_value(s.whatsapp_phone_number),
        whatsapp_phone_number_id_masked=_mask_value(s.whatsapp_phone_number_id),
        whatsapp_verified=s.whatsapp_verified,
        whatsapp_verified_at=s.whatsapp_verified_at.isoformat() if s.whatsapp_verified_at else None,
        whatsapp_sender_info=s.whatsapp_sender_info,
        whatsapp_last_delivery=s.whatsapp_last_delivery.isoformat() if s.whatsapp_last_delivery else None,
        whatsapp_last_error=s.whatsapp_last_error,
        server_whatsapp_configured=server_wa,
        whatsapp_provider=s.whatsapp_provider or settings.WHATSAPP_PROVIDER,

        in_app_enabled=s.in_app_enabled,
        in_app_status=in_app_status,
        in_app_verified_at=utc_now().isoformat(),

        all_coins=s.all_coins,
        selected_coins=selected_coins,
        available_symbols=settings.default_symbols,

        ml_alerts_enabled=s.ml_alerts_enabled,
        ml_min_confidence=s.ml_min_confidence,
        ml_min_edge=s.ml_min_edge,
        ml_notify_buy=s.ml_notify_buy,
        ml_notify_sell=s.ml_notify_sell,
        ml_notify_neutral=s.ml_notify_neutral,
        ml_timeframes=tf_list,

        news_alerts_enabled=s.news_alerts_enabled,
        news_categories=news_categories,

        risk_alerts_enabled=s.risk_alerts_enabled,
        notify_circuit_breaker=s.notify_circuit_breaker,
        notify_daily_loss=s.notify_daily_loss,
        notify_drawdown=s.notify_drawdown,
        notify_consecutive_losses=s.notify_consecutive_losses,
        notify_service_health=s.notify_service_health,

        delivery_mode=s.delivery_mode,
        summary_frequency=s.summary_frequency,
        summary_time=s.summary_time,
        summary_timezone=s.summary_timezone,
        last_summary_sent_at=s.last_summary_sent_at.isoformat() if s.last_summary_sent_at else None,

        env_writable=dep_ctx["env_writable"],
        is_cloud=dep_ctx["is_cloud"],
        platform=dep_ctx["platform"]
    )


# ============================================================================
# Channel Dedicated Configuration Endpoints
# ============================================================================

@notification_router.get("/deployment-context")
def get_channel_deployment_context():
    """Returns deployment environment context (local vs cloud, env writability)."""
    return get_deployment_context()


@notification_router.post("/channels/whatsapp/configure")
def configure_whatsapp_channel(
    req: ConfigureWhatsAppRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Securely verifies and configures WhatsApp Business Cloud API credentials.
    
    1. Validates recipient phone number using international E.164 formatting if provided.
    2. Validates credentials directly against the official Meta WhatsApp Graph API.
    3. Confirms Phone Number ID belongs to authorized WhatsApp Business Account.
    4. Persists verified configuration to database.
    5. Safely updates local .env if running locally and requested.
    """
    user_id = current_user.id if current_user else "sandbox_default"
    s = notification_service.get_or_create_settings(db, user_id)

    # 1. Recipient phone validation
    cleaned_recipient = None
    if req.recipient_phone:
        cleaned_recipient = req.recipient_phone.strip().replace(" ", "").replace("-", "")
        if not E164_REGEX.match(cleaned_recipient):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Recipient phone number must follow international E.164 format (e.g., +14155552671)."
            )

    # 2. Server-side verification with Meta Cloud API
    token = req.api_token.strip()
    phone_id = req.phone_number_id.strip()
    provider = (req.provider or "meta").strip().lower()

    is_valid, conn_status, message, meta = notification_service.verify_whatsapp_credentials(
        api_token=token,
        phone_number_id=phone_id,
        provider=provider
    )

    if not is_valid:
        s.whatsapp_status = conn_status
        s.whatsapp_last_error = message
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": conn_status,
                "message": message,
                "error": "WhatsApp credential verification failed with Meta API."
            }
        )

    # 3. Save validated configuration to user settings
    now_dt = utc_now()
    sender_info = (meta.get("verified_name") if meta else None) or "Meta WhatsApp Account"
    if meta and meta.get("display_phone_number"):
        sender_info += f" ({meta.get('display_phone_number')})"

    s.whatsapp_status = "CONNECTED"
    s.whatsapp_verified = True
    s.whatsapp_verified_at = now_dt
    s.whatsapp_sender_info = sender_info
    s.whatsapp_api_token = token
    s.whatsapp_phone_number_id = phone_id
    s.whatsapp_provider = provider
    s.whatsapp_enabled = True
    s.whatsapp_last_error = None
    if cleaned_recipient:
        s.whatsapp_phone_number = cleaned_recipient

    # 4. Atomic local .env synchronization (if local dev & requested)
    env_updated = False
    env_msg = "Credentials stored in database."
    if req.save_to_local_env:
        ok, msg = update_whitelisted_env_keys({
            "WHATSAPP_API_TOKEN": token,
            "WHATSAPP_PHONE_NUMBER_ID": phone_id,
            "WHATSAPP_ENABLED": "true",
            "WHATSAPP_PROVIDER": provider
        })
        env_updated = ok
        env_msg = msg

    db.commit()
    db.refresh(s)

    return {
        "status": "CONNECTED",
        "verified": True,
        "verified_at": now_dt.isoformat(),
        "sender_info": sender_info,
        "message": f"WhatsApp Business credentials verified successfully! {message}",
        "recipient_configured": bool(s.whatsapp_phone_number),
        "recipient_phone_masked": _mask_value(s.whatsapp_phone_number),
        "env_updated": env_updated,
        "env_message": env_msg
    }


@notification_router.post("/channels/telegram/configure")
def configure_telegram_channel(
    req: ConfigureTelegramRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Securely verifies and configures Telegram Bot credentials.
    
    1. Validates bot token via official Telegram Bot API (getMe).
    2. Validates chat ID access via getChat if provided.
    3. Persists verified configuration to database.
    4. Safely updates local .env if running locally and requested.
    """
    user_id = current_user.id if current_user else "sandbox_default"
    s = notification_service.get_or_create_settings(db, user_id)

    token = req.bot_token.strip()
    chat_id = req.chat_id.strip() if req.chat_id else None

    is_valid, conn_status, message, meta = notification_service.verify_telegram_credentials(
        bot_token=token,
        chat_id=chat_id
    )

    if not is_valid:
        s.telegram_status = conn_status
        s.telegram_last_error = message
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": conn_status,
                "message": message,
                "error": "Telegram credential verification failed."
            }
        )

    # Persist verified credentials
    now_dt = utc_now()
    sender_info = f"@{meta.get('bot_username')}" if meta and meta.get("bot_username") else "Telegram Bot"
    if meta and meta.get("chat_title"):
        sender_info += f" → {meta.get('chat_title')}"

    s.telegram_status = "CONNECTED"
    s.telegram_verified = True
    s.telegram_verified_at = now_dt
    s.telegram_sender_info = sender_info
    s.telegram_bot_token = token
    if chat_id:
        s.telegram_chat_id = chat_id
    s.telegram_enabled = True
    s.telegram_last_error = None

    env_updated = False
    env_msg = "Credentials stored in database."
    if req.save_to_local_env:
        env_dict = {
            "TELEGRAM_BOT_TOKEN": token,
            "TELEGRAM_ENABLED": "true"
        }
        if chat_id:
            env_dict["TELEGRAM_CHAT_ID"] = chat_id
        ok, msg = update_whitelisted_env_keys(env_dict)
        env_updated = ok
        env_msg = msg

    db.commit()
    db.refresh(s)

    return {
        "status": "CONNECTED",
        "verified": True,
        "verified_at": now_dt.isoformat(),
        "sender_info": sender_info,
        "message": f"Telegram Bot credentials verified successfully! {message}",
        "chat_id_configured": bool(s.telegram_chat_id),
        "chat_id_masked": _mask_value(s.telegram_chat_id),
        "env_updated": env_updated,
        "env_message": env_msg
    }


@notification_router.put("/settings")
def update_notification_settings(
    req: UpdateNotificationSettingsRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Updates user notification preferences and channel configurations."""
    user_id = current_user.id if current_user else "sandbox_default"
    s = notification_service.get_or_create_settings(db, user_id)

    if req.telegram_enabled is not None:
        s.telegram_enabled = req.telegram_enabled
    if req.telegram_bot_token is not None:
        s.telegram_bot_token = req.telegram_bot_token.strip() or None
    if req.telegram_chat_id is not None:
        s.telegram_chat_id = req.telegram_chat_id.strip() or None
        s.telegram_verified = False  # Reset until verified

    if req.whatsapp_enabled is not None:
        s.whatsapp_enabled = req.whatsapp_enabled
    if req.whatsapp_phone_number is not None:
        s.whatsapp_phone_number = req.whatsapp_phone_number.strip() or None
        s.whatsapp_verified = False

    if req.in_app_enabled is not None:
        s.in_app_enabled = req.in_app_enabled

    if req.all_coins is not None:
        s.all_coins = req.all_coins
    if req.selected_coins is not None:
        s.selected_coins_json = json.dumps(req.selected_coins)

    if req.ml_alerts_enabled is not None:
        s.ml_alerts_enabled = req.ml_alerts_enabled
    if req.ml_min_confidence is not None:
        s.ml_min_confidence = max(0.0, min(100.0, req.ml_min_confidence))
    if req.ml_min_edge is not None:
        s.ml_min_edge = max(0.0, min(100.0, req.ml_min_edge))
    if req.ml_notify_buy is not None:
        s.ml_notify_buy = req.ml_notify_buy
    if req.ml_notify_sell is not None:
        s.ml_notify_sell = req.ml_notify_sell
    if req.ml_notify_neutral is not None:
        s.ml_notify_neutral = req.ml_notify_neutral
    if req.ml_timeframes is not None:
        s.ml_timeframes = ",".join(req.ml_timeframes)

    if req.news_alerts_enabled is not None:
        s.news_alerts_enabled = req.news_alerts_enabled
    if req.news_categories is not None:
        s.news_categories_json = json.dumps(req.news_categories)

    if req.risk_alerts_enabled is not None:
        s.risk_alerts_enabled = req.risk_alerts_enabled
    if req.notify_circuit_breaker is not None:
        s.notify_circuit_breaker = req.notify_circuit_breaker
    if req.notify_daily_loss is not None:
        s.notify_daily_loss = req.notify_daily_loss
    if req.notify_drawdown is not None:
        s.notify_drawdown = req.notify_drawdown
    if req.notify_consecutive_losses is not None:
        s.notify_consecutive_losses = req.notify_consecutive_losses
    if req.notify_service_health is not None:
        s.notify_service_health = req.notify_service_health

    if req.delivery_mode is not None:
        if req.delivery_mode in ["instant", "summary", "both"]:
            s.delivery_mode = req.delivery_mode
    if req.summary_frequency is not None:
        if req.summary_frequency in ["hourly", "daily", "weekly"]:
            s.summary_frequency = req.summary_frequency
    if req.summary_time is not None:
        s.summary_time = req.summary_time
    if req.summary_timezone is not None:
        s.summary_timezone = req.summary_timezone

    s.updated_at = utc_now()
    db.commit()
    db.refresh(s)

    return get_notification_settings(db=db, current_user=current_user)


@notification_router.post("/test/{channel}")
def test_notification_channel(
    channel: str,
    req: TestNotificationRequest = TestNotificationRequest(),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Dispatches a live verification test alert to Telegram, WhatsApp, or In-App."""
    user_id = current_user.id if current_user else "sandbox_default"
    result = notification_service.send_test_notification(
        db=db,
        user_id=user_id,
        channel=channel.lower().strip(),
        token_override=req.token_override,
        chat_id_override=req.chat_id_override,
        phone_override=req.phone_override
    )
    return result


# ============================================================================
# Price Alert Rules Endpoints
# ============================================================================

@notification_router.get("/price-rules", response_model=List[PriceAlertRuleResponse])
def get_price_rules(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Lists all active and configured price alert rules for the current user."""
    user_id = current_user.id if current_user else "sandbox_default"
    rules = db.query(PriceAlertRule).filter(PriceAlertRule.user_id == user_id).order_by(PriceAlertRule.created_at.desc()).all()

    return [
        PriceAlertRuleResponse(
            id=r.id,
            user_id=r.user_id,
            symbol=r.symbol,
            condition_type=r.condition_type,
            lower_boundary=r.lower_boundary,
            upper_boundary=r.upper_boundary,
            target_price=r.target_price,
            channels=r.channels,
            is_active=r.is_active,
            last_evaluated_price=r.last_evaluated_price,
            last_state=r.last_state,
            last_triggered_at=r.last_triggered_at.isoformat() if r.last_triggered_at else None,
            cooldown_seconds=r.cooldown_seconds,
            created_at=r.created_at.isoformat()
        )
        for r in rules
    ]


@notification_router.post("/price-rules", response_model=PriceAlertRuleResponse)
def create_price_rule(
    req: PriceAlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Creates a new price-range or price-crossing rule with strict validation."""
    user_id = current_user.id if current_user else "sandbox_default"
    sym = req.symbol.upper().strip()

    valid_types = ["entering_range", "exiting_range", "crossing_up", "crossing_down"]
    if req.condition_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid condition_type. Must be one of: {valid_types}"
        )

    if req.condition_type in ["entering_range", "exiting_range"]:
        if req.lower_boundary is None or req.upper_boundary is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both lower_boundary and upper_boundary are required for range conditions."
            )
        if req.lower_boundary <= 0 or req.upper_boundary <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price boundaries must be positive numbers."
            )
        if req.lower_boundary >= req.upper_boundary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="lower_boundary must be strictly less than upper_boundary."
            )
    else:
        if req.target_price is None or req.target_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_price must be a positive number for price crossing conditions."
            )

    rule = PriceAlertRule(
        id=str(uuid.uuid4()),
        user_id=user_id,
        symbol=sym,
        condition_type=req.condition_type,
        lower_boundary=req.lower_boundary,
        upper_boundary=req.upper_boundary,
        target_price=req.target_price,
        channels=req.channels or "in_app,telegram",
        is_active=True,
        cooldown_seconds=req.cooldown_seconds or 300,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    return PriceAlertRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        symbol=rule.symbol,
        condition_type=rule.condition_type,
        lower_boundary=rule.lower_boundary,
        upper_boundary=rule.upper_boundary,
        target_price=rule.target_price,
        channels=rule.channels,
        is_active=rule.is_active,
        last_evaluated_price=rule.last_evaluated_price,
        last_state=rule.last_state,
        last_triggered_at=None,
        cooldown_seconds=rule.cooldown_seconds,
        created_at=rule.created_at.isoformat()
    )


@notification_router.put("/price-rules/{rule_id}")
def update_price_rule(
    rule_id: str,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Toggles active state of a price alert rule."""
    user_id = current_user.id if current_user else "sandbox_default"
    rule = db.query(PriceAlertRule).filter(
        PriceAlertRule.id == rule_id,
        PriceAlertRule.user_id == user_id
    ).first()

    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")

    if is_active is not None:
        rule.is_active = is_active
        rule.updated_at = utc_now()
        db.commit()

    return {"status": "success", "is_active": rule.is_active}


@notification_router.delete("/price-rules/{rule_id}")
def delete_price_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Deletes a price alert rule for the current user."""
    user_id = current_user.id if current_user else "sandbox_default"
    rule = db.query(PriceAlertRule).filter(
        PriceAlertRule.id == rule_id,
        PriceAlertRule.user_id == user_id
    ).first()

    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")

    db.delete(rule)
    db.commit()
    return {"status": "success", "message": "Price rule deleted."}


# ============================================================================
# In-App Notifications Endpoints
# ============================================================================

@notification_router.get("/in-app")
def get_in_app_notifications(
    category: Optional[str] = None,
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves paginated persistent in-app notifications for the user."""
    user_id = current_user.id if current_user else "sandbox_default"
    q = db.query(InAppNotification).filter(InAppNotification.user_id == user_id)

    if category:
        q = q.filter(InAppNotification.category == category)
    if unread_only:
        q = q.filter(InAppNotification.is_read == False)

    total = q.count()
    items = q.order_by(InAppNotification.created_at.desc()).offset(offset).limit(limit).all()

    formatted = []
    for it in items:
        meta = {}
        if it.metadata_json:
            try:
                meta = json.loads(it.metadata_json)
            except Exception:
                meta = {}
        formatted.append({
            "id": it.id,
            "title": it.title,
            "message": it.message,
            "category": it.category,
            "severity": it.severity,
            "symbol": it.symbol,
            "metadata": meta,
            "is_read": it.is_read,
            "created_at": it.created_at.isoformat()
        })

    return {
        "status": "success",
        "total": total,
        "count": len(formatted),
        "notifications": formatted
    }


@notification_router.get("/in-app/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Returns number of unread in-app alerts for header notification badge."""
    user_id = current_user.id if current_user else "sandbox_default"
    count = db.query(InAppNotification).filter(
        InAppNotification.user_id == user_id,
        InAppNotification.is_read == False
    ).count()
    return {"unread_count": count}


@notification_router.post("/in-app/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Marks a single in-app notification as read."""
    user_id = current_user.id if current_user else "sandbox_default"
    notif = db.query(InAppNotification).filter(
        InAppNotification.id == notification_id,
        InAppNotification.user_id == user_id
    ).first()

    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    notif.is_read = True
    db.commit()
    return {"status": "success", "is_read": True}


@notification_router.post("/in-app/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Marks all user in-app notifications as read."""
    user_id = current_user.id if current_user else "sandbox_default"
    db.query(InAppNotification).filter(
        InAppNotification.user_id == user_id,
        InAppNotification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"status": "success", "message": "All notifications marked as read."}


@notification_router.delete("/in-app/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Deletes an in-app notification."""
    user_id = current_user.id if current_user else "sandbox_default"
    notif = db.query(InAppNotification).filter(
        InAppNotification.id == notification_id,
        InAppNotification.user_id == user_id
    ).first()

    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    db.delete(notif)
    db.commit()
    return {"status": "success"}


# ============================================================================
# Audit Logs & Summary Trigger
# ============================================================================

@notification_router.get("/delivery-history")
def get_delivery_history(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Returns audit trail of recent notification delivery attempts."""
    user_id = current_user.id if current_user else "sandbox_default"
    logs = db.query(NotificationDeliveryLog).filter(
        NotificationDeliveryLog.user_id == user_id
    ).order_by(NotificationDeliveryLog.created_at.desc()).limit(limit).all()

    return [
        {
            "id": l.id,
            "channel": l.channel,
            "category": l.category,
            "status": l.status,
            "recipient": l.recipient,
            "error_message": l.error_message,
            "payload_preview": l.payload_preview,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]


@notification_router.post("/summary/trigger-now")
def trigger_summary_now(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Manually generates and dispatches hourly market summary for testing."""
    user_id = current_user.id if current_user else None
    dispatched = notification_service.run_scheduled_summaries(db, user_id=user_id, force=True)
    return {
        "status": "success",
        "message": "Hourly market summary dispatch executed successfully.",
        "dispatched_count": dispatched
    }
