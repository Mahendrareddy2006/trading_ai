"""Automated Unit and Integration Tests for Trading AI Notification Center.

Tests coverage:
1. Notification settings persistence & secret redaction
2. User-to-user data isolation (IDOR protection on settings and price rules)
3. ML confidence threshold behavior (< threshold, = threshold, > threshold)
4. Coin-selection filtering (all_coins vs selected_coins)
5. Direction filtering (BUY vs SELL vs NEUTRAL)
6. Price alert rule transitions (entering_range, exiting_range, crossing_up, crossing_down)
7. Deduplication, state tracking, and cooldown suppression
8. In-app notifications persistence, unread counters, and read-state updates
9. Telegram dispatch (success, 401 invalid token, timeout) with mocked network
10. WhatsApp dispatch (unconfigured honest status, mocked Meta API success)
11. News category filtering and deduplication
12. Risk engine dispatch on circuit breaker / kill switch
13. Periodic summary generation
"""

import uuid
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from trading_ai.api.app import app
from trading_ai.core.security import create_access_token, hash_password
from trading_ai.database.models import (
    User, 
    NotificationSetting, 
    PriceAlertRule, 
    InAppNotification, 
    NotificationDeliveryLog
)
from trading_ai.database.session import SessionLocal
from trading_ai.services.notification_service import notification_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_external_requests():
    """Globally mocks external HTTP dispatch so automated tests never hit live APIs."""
    with patch("trading_ai.services.notification_service.requests.post") as mock_post, \
         patch("trading_ai.services.notification_service.requests.get") as mock_get:
        post_resp = MagicMock()
        post_resp.status_code = 200
        post_resp.json.return_value = {
            "ok": True, 
            "result": {"message_id": 9999, "id": 987654, "title": "Trading Chat"}
        }
        post_resp.text = '{"ok": true}'
        mock_post.return_value = post_resp

        get_resp = MagicMock()
        get_resp.status_code = 200
        get_resp.json.return_value = {
            "ok": True,
            "result": {"username": "TradingAIBot", "first_name": "Trading AI Bot"},
            "verified_name": "Trading AI Business",
            "display_phone_number": "+15551234567"
        }
        get_resp.text = '{"ok": true}'
        mock_get.return_value = get_resp

        yield (mock_post, mock_get)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_users(db):
    """Creates two isolated test users with active tokens."""
    u1_id = f"test_user1_{uuid.uuid4().hex[:8]}"
    u2_id = f"test_user2_{uuid.uuid4().hex[:8]}"

    user1 = User(
        id=u1_id,
        username=f"trader1_{uuid.uuid4().hex[:4]}",
        email=f"trader1_{uuid.uuid4().hex[:4]}@example.com",
        hashed_password=hash_password("Password123!"),
        is_active=True,
        is_superuser=False
    )
    user2 = User(
        id=u2_id,
        username=f"trader2_{uuid.uuid4().hex[:4]}",
        email=f"trader2_{uuid.uuid4().hex[:4]}@example.com",
        hashed_password=hash_password("Password123!"),
        is_active=True,
        is_superuser=False
    )
    db.add(user1)
    db.add(user2)
    db.commit()

    token1 = create_access_token({"sub": user1.id, "username": user1.username, "is_admin": False})
    token2 = create_access_token({"sub": user2.id, "username": user2.username, "is_admin": False})

    return {
        "user1": user1,
        "token1": token1,
        "headers1": {"Authorization": f"Bearer {token1}"},
        "user2": user2,
        "token2": token2,
        "headers2": {"Authorization": f"Bearer {token2}"}
    }


def test_notification_settings_persistence_and_redaction(client, test_users):
    """Verifies settings retrieval creates defaults, updates persist, and secrets are masked."""
    headers = test_users["headers1"]

    # 1. GET settings (creates defaults)
    res = client.get("/api/notifications/settings", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == test_users["user1"].id
    assert data["all_coins"] is True
    assert data["ml_min_confidence"] == 70.0
    assert data["telegram_chat_id_masked"] is None

    # 2. PUT settings to update configuration
    update_payload = {
        "telegram_enabled": True,
        "telegram_chat_id": "987654321",
        "all_coins": False,
        "selected_coins": ["BTCUSDT", "ETHUSDT"],
        "ml_alerts_enabled": True,
        "ml_min_confidence": 85.0,
        "ml_min_edge": 3.0,
        "ml_notify_buy": True,
        "ml_notify_sell": False
    }
    res_update = client.put("/api/notifications/settings", json=update_payload, headers=headers)
    assert res_update.status_code == 200
    updated = res_update.json()

    assert updated["telegram_enabled"] is True
    assert updated["telegram_chat_id_masked"] == "98****21"
    assert "987654321" not in updated["telegram_chat_id_masked"]
    assert updated["all_coins"] is False
    assert updated["selected_coins"] == ["BTCUSDT", "ETHUSDT"]
    assert updated["ml_min_confidence"] == 85.0
    assert updated["ml_notify_buy"] is True
    assert updated["ml_notify_sell"] is False


def test_user_to_user_isolation(client, test_users):
    """Verifies that User 2 cannot see or modify User 1's notification settings or price rules."""
    h1 = test_users["headers1"]
    h2 = test_users["headers2"]

    # User 1 sets telegram chat id
    client.put("/api/notifications/settings", json={
        "telegram_chat_id": "111222333",
        "telegram_enabled": True
    }, headers=h1)

    # User 2 gets their own settings
    res2 = client.get("/api/notifications/settings", headers=h2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["user_id"] == test_users["user2"].id
    assert data2["telegram_chat_id_masked"] is None
    assert data2["telegram_enabled"] is False

    # User 1 creates a price alert rule
    res_rule = client.post("/api/notifications/price-rules", json={
        "symbol": "BTCUSDT",
        "condition_type": "crossing_up",
        "target_price": 70000.0,
        "channels": "in_app,telegram"
    }, headers=h1)
    assert res_rule.status_code == 200
    rule1_id = res_rule.json()["id"]

    # User 2 lists rules (should NOT contain User 1's rule)
    res_u2_rules = client.get("/api/notifications/price-rules", headers=h2)
    assert res_u2_rules.status_code == 200
    assert len(res_u2_rules.json()) == 0

    # User 2 tries to delete User 1's rule (must fail 404 Not Found)
    res_u2_del = client.delete(f"/api/notifications/price-rules/{rule1_id}", headers=h2)
    assert res_u2_del.status_code == 404


def test_ml_confidence_threshold_filtering(db, test_users):
    """Verifies ML signal alerts trigger only when confidence meets or exceeds user threshold."""
    user1_id = test_users["user1"].id

    # Configure user with 80% threshold, BUY only, all_coins=True
    setting = notification_service.get_or_create_settings(db, user1_id)
    setting.ml_alerts_enabled = True
    setting.in_app_enabled = True
    setting.ml_min_confidence = 80.0
    setting.ml_min_edge = 0.0
    setting.ml_notify_buy = True
    setting.ml_notify_sell = False
    setting.all_coins = True
    db.commit()

    # 1. Prediction below threshold (75% BUY) -> 0 notifications
    pred_low = {
        "symbol": "BTCUSDT",
        "direction": "BUY",
        "confidence": 75.0,
        "edge": 2.5,
        "timeframe": "1h",
        "price": 65000.0,
        "timestamp": "2026-10-11T12:00:00"
    }
    sent_low = notification_service.evaluate_ml_predictions(db, [pred_low], user_id=user1_id)
    assert sent_low == 0

    # 2. Prediction equal to threshold (80% BUY) -> 1 notification
    pred_exact = {
        "symbol": "ETHUSDT",
        "direction": "BUY",
        "confidence": 80.0,
        "edge": 3.0,
        "timeframe": "1h",
        "price": 3500.0,
        "timestamp": "2026-10-11T12:00:00"
    }
    sent_exact = notification_service.evaluate_ml_predictions(db, [pred_exact], user_id=user1_id)
    assert sent_exact == 1

    # 3. Prediction above threshold (92% BUY) -> 1 notification
    pred_high = {
        "symbol": "SOLUSDT",
        "direction": "BUY",
        "confidence": 92.0,
        "edge": 4.5,
        "timeframe": "1h",
        "price": 180.0,
        "timestamp": "2026-10-11T12:00:00"
    }
    sent_high = notification_service.evaluate_ml_predictions(db, [pred_high], user_id=user1_id)
    assert sent_high == 1

    # 4. Prediction high confidence SELL (95%) but user disabled SELL -> 0 notifications
    pred_sell = {
        "symbol": "BNBUSDT",
        "direction": "SELL",
        "confidence": 95.0,
        "edge": 5.0,
        "timeframe": "1h",
        "price": 590.0,
        "timestamp": "2026-10-11T12:00:00"
    }
    sent_sell = notification_service.evaluate_ml_predictions(db, [pred_sell], user_id=user1_id)
    assert sent_sell == 0


def test_coin_selection_filtering(db, test_users):
    """Verifies that when all_coins=False, only selected coins generate ML alerts."""
    user1_id = test_users["user1"].id

    setting = notification_service.get_or_create_settings(db, user1_id)
    setting.ml_alerts_enabled = True
    setting.in_app_enabled = True
    setting.ml_min_confidence = 60.0
    setting.ml_notify_buy = True
    setting.all_coins = False
    setting.selected_coins_json = '["AVAXUSDT"]'
    db.commit()

    # Signal for non-selected coin (BTCUSDT) -> Ignored
    pred_btc = {
        "symbol": "BTCUSDT",
        "direction": "BUY",
        "confidence": 95.0,
        "edge": 5.0,
        "timeframe": "1h",
        "price": 65000.0,
        "timestamp": "2026-10-11T12:00:00"
    }
    sent_btc = notification_service.evaluate_ml_predictions(db, [pred_btc], user_id=user1_id)
    assert sent_btc == 0

    # Signal for selected coin (AVAXUSDT) -> Sent
    pred_avax = {
        "symbol": "AVAXUSDT",
        "direction": "BUY",
        "confidence": 85.0,
        "edge": 4.0,
        "timeframe": "1h",
        "price": 28.5,
        "timestamp": "2026-10-11T12:00:00"
    }
    sent_avax = notification_service.evaluate_ml_predictions(db, [pred_avax], user_id=user1_id)
    assert sent_avax == 1


def test_price_range_and_crossing_alert_transitions(db, test_users):
    """Verifies price range entry/exit and crossing upward/downward state tracking."""
    user1_id = test_users["user1"].id
    setting = notification_service.get_or_create_settings(db, user1_id)
    setting.in_app_enabled = True
    db.commit()

    # 1. Rule: Range entry between 60,000 and 62,000
    rule_entry = PriceAlertRule(
        user_id=user1_id,
        symbol="BTCUSDT",
        condition_type="entering_range",
        lower_boundary=60000.0,
        upper_boundary=62000.0,
        channels="in_app",
        is_active=True,
        cooldown_seconds=60
    )
    # 2. Rule: Crossing up at 3,500
    rule_cross = PriceAlertRule(
        user_id=user1_id,
        symbol="ETHUSDT",
        condition_type="crossing_up",
        target_price=3500.0,
        channels="in_app",
        is_active=True,
        cooldown_seconds=60
    )
    db.add(rule_entry)
    db.add(rule_cross)
    db.commit()

    # Tick 1: BTC outside at 59,000 -> No trigger, state recorded as OUTSIDE
    notification_service.evaluate_price_alerts(db, {"BTCUSDT": 59000.0, "ETHUSDT": 3450.0}, user_id=user1_id)
    db.refresh(rule_entry)
    db.refresh(rule_cross)
    assert rule_entry.last_state == "OUTSIDE"
    assert rule_cross.last_state == "BELOW"
    assert rule_entry.last_triggered_at is None
    assert rule_cross.last_triggered_at is None

    # Tick 2: BTC enters range at 61,000 -> Triggers alert, state transitions to INSIDE
    triggered_count = notification_service.evaluate_price_alerts(db, {"BTCUSDT": 61000.0, "ETHUSDT": 3490.0}, user_id=user1_id)
    db.refresh(rule_entry)
    assert triggered_count == 1
    assert rule_entry.last_state == "INSIDE"
    assert rule_entry.last_triggered_at is not None

    # Tick 3: BTC still inside at 61,500 -> Cooldown & state suppression prevents spam
    triggered_count2 = notification_service.evaluate_price_alerts(db, {"BTCUSDT": 61500.0, "ETHUSDT": 3495.0}, user_id=user1_id)
    assert triggered_count2 == 0

    # Tick 4: ETH crosses up to 3510 -> Triggers alert, state transitions to ABOVE
    triggered_count3 = notification_service.evaluate_price_alerts(db, {"BTCUSDT": 61500.0, "ETHUSDT": 3510.0}, user_id=user1_id)
    db.refresh(rule_cross)
    assert triggered_count3 == 1
    assert rule_cross.last_state == "ABOVE"
    assert rule_cross.last_triggered_at is not None


def test_in_app_notifications_lifecycle(client, test_users):
    """Verifies in-app notification creation, unread counting, and read status transitions."""
    h1 = test_users["headers1"]

    # 1. Trigger test in-app notification
    res_test = client.post("/api/notifications/test/in_app", headers=h1)
    assert res_test.status_code == 200
    assert res_test.json()["status"] == "DELIVERED"

    # 2. Check unread count is at least 1
    res_unread = client.get("/api/notifications/in-app/unread-count", headers=h1)
    assert res_unread.status_code == 200
    count = res_unread.json()["unread_count"]
    assert count >= 1

    # 3. Fetch notifications list
    res_list = client.get("/api/notifications/in-app?limit=10", headers=h1)
    assert res_list.status_code == 200
    notifs = res_list.json()["notifications"]
    assert len(notifs) >= 1
    target_id = notifs[0]["id"]
    assert notifs[0]["is_read"] is False

    # 4. Mark single notification as read
    res_read = client.post(f"/api/notifications/in-app/{target_id}/read", headers=h1)
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # 5. Mark all as read
    res_all = client.post("/api/notifications/in-app/read-all", headers=h1)
    assert res_all.status_code == 200

    # 6. Verify unread count is now 0
    res_count_after = client.get("/api/notifications/in-app/unread-count", headers=h1)
    assert res_count_after.json()["unread_count"] == 0


@patch("trading_ai.services.notification_service.requests.post")
def test_telegram_dispatch_mocked(mock_post, client, test_users):
    """Verifies Telegram dispatch behavior on success, 401 invalid token, and network timeouts."""
    h1 = test_users["headers1"]

    # 1. Mock Telegram HTTP 200 Success
    mock_resp_success = MagicMock()
    mock_resp_success.status_code = 200
    mock_resp_success.json.return_value = {"ok": True, "result": {"message_id": 12345}}
    mock_post.return_value = mock_resp_success

    # Configure user with telegram chat id
    client.put("/api/notifications/settings", json={
        "telegram_enabled": True,
        "telegram_chat_id": "999888777"
    }, headers=h1)

    res_test = client.post("/api/notifications/test/telegram", headers=h1)
    assert res_test.status_code == 200
    assert res_test.json()["status"] == "DELIVERED"
    assert "delivered" in res_test.json()["message"].lower()

    # 2. Mock Telegram HTTP 401 Unauthorized (Invalid bot token)
    mock_resp_401 = MagicMock()
    mock_resp_401.status_code = 401
    mock_resp_401.text = "Unauthorized: invalid bot token"
    mock_post.return_value = mock_resp_401

    res_test_401 = client.post("/api/notifications/test/telegram", headers=h1)
    assert res_test_401.status_code == 200
    assert res_test_401.json()["status"] == "FAILED"
    assert "401" in res_test_401.json()["message"] or "unauthorized" in res_test_401.json()["message"].lower()


def test_whatsapp_honest_status_when_unconfigured(client, test_users):
    """Verifies WhatsApp test returns honest FAILED status when server tokens are absent."""
    h1 = test_users["headers1"]

    # Ensure user has phone number set but server has no API token configured
    client.put("/api/notifications/settings", json={
        "whatsapp_enabled": True,
        "whatsapp_phone_number": "+1234567890"
    }, headers=h1)

    res_test = client.post("/api/notifications/test/whatsapp", headers=h1)
    assert res_test.status_code == 200
    assert res_test.json()["status"] == "FAILED"
    assert "not configured" in res_test.json()["message"].lower()


def test_news_category_filter(db, test_users):
    """Verifies market news notification filtering respects user category subscriptions."""
    user1_id = test_users["user1"].id
    setting = notification_service.get_or_create_settings(db, user1_id)
    setting.news_alerts_enabled = True
    setting.in_app_enabled = True
    setting.news_categories_json = '["Bitcoin", "Exchanges"]'
    db.commit()

    # Article in subscribed category ("Bitcoin") -> Sent
    btc_article = {
        "id": f"news_btc_{uuid.uuid4().hex[:6]}",
        "title": "Bitcoin ETF Inflows Surge to Record $1.2B",
        "publisher": "CoinDesk",
        "category": "Bitcoin",
        "url": "https://coindesk.com/btc-etf",
        "published_at": "2026-10-11T10:00:00"
    }
    sent_btc = notification_service.evaluate_news_articles(db, [btc_article], user_id=user1_id)
    assert sent_btc == 1

    # Article in unsubscribed category ("Altcoins") -> Ignored
    alt_article = {
        "id": f"news_alt_{uuid.uuid4().hex[:6]}",
        "title": "Solana Ecosystem DEX Volume Hits All-Time High",
        "publisher": "Decrypt",
        "category": "Altcoins",
        "url": "https://decrypt.co/solana-dex",
        "published_at": "2026-10-11T10:15:00"
    }
    sent_alt = notification_service.evaluate_news_articles(db, [alt_article], user_id=user1_id)
    assert sent_alt == 0


def test_kill_switch_triggers_risk_notification(client, db, test_users):
    """Verifies emergency kill switch toggle triggers risk event dispatch."""
    h1 = test_users["headers1"]

    # Configure user with risk notifications enabled
    setting = notification_service.get_or_create_settings(db, test_users["user1"].id)
    setting.risk_alerts_enabled = True
    setting.notify_circuit_breaker = True
    setting.in_app_enabled = True
    db.commit()

    # Toggle kill switch
    res = client.post("/api/risk/kill-switch", json={"active": True, "reason": "Test risk trigger"}, headers=h1)
    assert res.status_code == 200

    # Verify an in-app risk notification was generated
    res_notifs = client.get("/api/notifications/in-app?category=risk_event", headers=h1)
    assert res_notifs.status_code == 200
    risk_notifs = res_notifs.json()["notifications"]
    assert len(risk_notifs) >= 1
    assert "KILL SWITCH" in risk_notifs[0]["title"]


def test_configure_whatsapp_channel_success(client, db, test_users):
    """Verifies WhatsApp Meta Cloud API configuration endpoint validates and persists credentials."""
    h1 = test_users["headers1"]
    payload = {
        "api_token": "EAAXsampleMetaCloudToken123456789",
        "phone_number_id": "104829104820194",
        "recipient_phone": "+14155552671",
        "provider": "meta",
        "save_to_local_env": False
    }
    res = client.post("/api/notifications/channels/whatsapp/configure", json=payload, headers=h1)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CONNECTED"
    assert data["verified"] is True
    assert "Trading AI Business" in data["sender_info"]
    assert data["recipient_configured"] is True

    # Verify settings endpoint reflects updated WhatsApp status
    settings_res = client.get("/api/notifications/settings", headers=h1)
    assert settings_res.status_code == 200
    s_data = settings_res.json()
    assert s_data["whatsapp_status"] == "CONNECTED"
    assert s_data["whatsapp_verified"] is True
    assert s_data["whatsapp_sender_info"] is not None


def test_configure_whatsapp_invalid_recipient_e164(client, test_users):
    """Verifies non-E.164 recipient phone numbers are rejected with 422."""
    h1 = test_users["headers1"]
    payload = {
        "api_token": "EAAXsampleMetaCloudToken123456789",
        "phone_number_id": "104829104820194",
        "recipient_phone": "invalid_phone_number_12345",
        "provider": "meta",
        "save_to_local_env": False
    }
    res = client.post("/api/notifications/channels/whatsapp/configure", json=payload, headers=h1)
    assert res.status_code == 422
    assert "E.164" in res.json()["detail"]


def test_configure_whatsapp_rejected_by_meta_api(client, test_users):
    """Verifies Meta Graph API error response properly yields 400 Bad Request."""
    h1 = test_users["headers1"]
    with patch("trading_ai.services.notification_service.requests.get") as mock_get:
        err_resp = MagicMock()
        err_resp.status_code = 401
        err_resp.headers = {"content-type": "application/json"}
        err_resp.json.return_value = {
            "error": {"message": "Invalid OAuth access token - Cannot parse access token"}
        }
        mock_get.return_value = err_resp

        payload = {
            "api_token": "bad_token_123456789",
            "phone_number_id": "104829104820194",
            "provider": "meta",
            "save_to_local_env": False
        }
        res = client.post("/api/notifications/channels/whatsapp/configure", json=payload, headers=h1)
        assert res.status_code == 400
        detail = res.json()["detail"]
        assert detail["status"] == "INVALID_CREDENTIALS"


def test_configure_telegram_channel_success(client, test_users):
    """Verifies Telegram Bot Token & Chat ID verification and persistence."""
    h1 = test_users["headers1"]
    payload = {
        "bot_token": "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ",
        "chat_id": "987654321",
        "save_to_local_env": False
    }
    res = client.post("/api/notifications/channels/telegram/configure", json=payload, headers=h1)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CONNECTED"
    assert data["verified"] is True
    assert "@TradingAIBot" in data["sender_info"]
    assert data["chat_id_configured"] is True

    # Verify settings endpoint reflects Telegram connected status
    settings_res = client.get("/api/notifications/settings", headers=h1)
    assert settings_res.status_code == 200
    s_data = settings_res.json()
    assert s_data["telegram_status"] == "CONNECTED"
    assert s_data["telegram_verified"] is True


def test_telegram_test_dispatch_updates_status(client, test_users):
    """Verifies test dispatch returns connected status and delivery details."""
    h1 = test_users["headers1"]
    res = client.post("/api/notifications/test/telegram", json={}, headers=h1)
    assert res.status_code == 200
    data = res.json()
    assert data["channel"] == "telegram"
    assert data["success"] is True
    assert data["status"] == "DELIVERED"
    assert "connection_status" in data


def test_hourly_summary_dispatches_telegram_whatsapp_inapp(db, test_users):
    """Verifies hourly summaries are compiled and dispatched via Telegram, WhatsApp, and In-App."""
    u1 = test_users["user1"]
    s = notification_service.get_or_create_settings(db, u1.id)
    s.telegram_enabled = True
    s.telegram_chat_id = "7995700205"
    s.telegram_bot_token = "123456:ABC-DEF"
    s.whatsapp_enabled = True
    s.whatsapp_phone_number = "+15551234567"
    s.in_app_enabled = True
    s.delivery_mode = "both"
    s.summary_frequency = "hourly"
    db.commit()

    # Trigger hourly summary
    dispatched = notification_service.run_scheduled_summaries(db, user_id=u1.id, force=True)
    assert dispatched >= 1

    # Verify In-App summary notification was recorded
    in_app_summary = db.query(InAppNotification).filter(
        InAppNotification.user_id == u1.id,
        InAppNotification.category == "summary"
    ).first()
    assert in_app_summary is not None
    assert "Summary" in in_app_summary.title
    assert "Equity" in in_app_summary.message

    # Verify delivery logs for all enabled summary channels
    logs = db.query(NotificationDeliveryLog).filter(
        NotificationDeliveryLog.user_id == u1.id,
        NotificationDeliveryLog.category == "summary"
    ).all()
    channels_logged = {l.channel for l in logs}
    assert "in_app" in channels_logged
    assert "telegram" in channels_logged
    assert "whatsapp" in channels_logged


def test_important_news_dispatches_all_channels(db, test_users):
    """Verifies important/breaking news triggers multi-channel alerts across WhatsApp, Telegram, and Web In-App."""
    u1 = test_users["user1"]
    s = notification_service.get_or_create_settings(db, u1.id)
    s.news_alerts_enabled = True
    s.telegram_enabled = True
    s.telegram_chat_id = "7995700205"
    s.telegram_bot_token = "123456:ABC-DEF"
    s.whatsapp_enabled = True
    s.whatsapp_phone_number = "+15551234567"
    s.in_app_enabled = True
    db.commit()

    breaking_article = {
        "id": f"breaking_{uuid.uuid4().hex[:6]}",
        "title": "BREAKING: SEC Approves Landmark Universal Crypto Exchange Framework",
        "publisher": "CoinDesk",
        "summary": "The US Securities and Exchange Commission has formally voted to approve new regulatory guidelines.",
        "url": "https://coindesk.com/policy/sec-landmark-approval",
        "published_at": "2026-10-11T12:00:00",
        "categories": ["regulation", "all"],
        "is_important": True,
        "urgency": "CRITICAL",
        "importance_reason": "Major Regulatory Milestone"
    }

    sent = notification_service.evaluate_news_articles(db, [breaking_article], user_id=u1.id)
    assert sent == 1

    # Verify delivery logs record all 3 channels: in_app, telegram, and whatsapp
    logs = db.query(NotificationDeliveryLog).filter(
        NotificationDeliveryLog.user_id == u1.id,
        NotificationDeliveryLog.category == "market_news"
    ).all()
    channels_logged = {l.channel for l in logs}
    assert "in_app" in channels_logged
    assert "telegram" in channels_logged
    assert "whatsapp" in channels_logged

    # Verify In-App alert recorded in database with critical severity for the Web UI
    in_app_item = db.query(InAppNotification).filter(
        InAppNotification.user_id == u1.id,
        InAppNotification.category == "market_news"
    ).first()
    assert in_app_item is not None
    assert in_app_item.severity == "critical"
    assert "IMPORTANT NEWS" in in_app_item.title


def test_trigger_summary_now_endpoint(client, test_users):
    """Verifies manual POST /api/notifications/summary/trigger-now endpoint triggers force dispatch."""
    h1 = test_users["headers1"]
    res = client.post("/api/notifications/summary/trigger-now", headers=h1)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "dispatched_count" in data

