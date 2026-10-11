"""Production Security, Multi-User Isolation, and Paper Execution Test Suite.

Verifies:
1. 20+ active USDT perpetual symbols configuration
2. Signup disabled by default (private preview gate)
3. Authentication and JWT verification
4. User-scoped credential encryption at rest (AES-256-GCM / Fernet)
5. Cross-user data isolation and IDOR prevention
6. Paper-only execution barrier (zero live order execution paths)
7. Rate limiting on sensitive auth endpoints
8. Per-user watchlist isolation
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from trading_ai.api.app import app
from trading_ai.config.settings import settings
from trading_ai.core.security import (
    encrypt_credential,
    decrypt_credential,
    mask_api_key,
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    check_rate_limit
)
from trading_ai.database.models import User, ExchangeCredential, UserWatchlist
from trading_ai.database.session import SessionLocal
from trading_ai.execution.binance_client import BinanceFuturesClient


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


def test_20_active_symbols_configuration():
    """Verifies that at least 20 active USD(S)-M Futures symbols are configured."""
    symbols = settings.default_symbols
    assert len(symbols) >= 20, f"Expected >= 20 symbols, found {len(symbols)}"
    for s in symbols:
        assert s.endswith("USDT"), f"Symbol {s} must be a USDT perpetual instrument"
        assert s.isupper()
        assert len(s) >= 6


def test_signup_disabled_by_default(client):
    """Verifies public signup returns 403 Forbidden when ALLOW_PUBLIC_SIGNUP=False."""
    assert settings.ALLOW_PUBLIC_SIGNUP is False

    res = client.post("/api/auth/register", json={
        "username": f"unauthorized_{uuid.uuid4().hex[:6]}",
        "email": f"unauthorized_{uuid.uuid4().hex[:6]}@test.com",
        "password": "Password123!"
    })
    assert res.status_code == 403
    assert "Public registration is currently disabled" in res.json().get("detail", "")


def test_password_hashing_and_verification():
    """Verifies scrypt-based password hashing with unique salts."""
    pwd = "UltraSecurePassword456!"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)

    # Different salts must yield different hashes
    assert h1 != h2
    assert verify_password(pwd, h1) is True
    assert verify_password(pwd, h2) is True
    assert verify_password("WrongPassword!", h1) is False


def test_credential_encryption_at_rest():
    """Verifies AES-256-GCM / Fernet authenticated encryption and decryption."""
    secret = "my_binance_api_secret_32bytes_value"
    encrypted = encrypt_credential(secret)

    # Encrypted value must not contain the plaintext secret
    assert secret not in encrypted
    assert len(encrypted) > len(secret)

    decrypted = decrypt_credential(encrypted)
    assert decrypted == secret

    # Tampered ciphertext must fail decryption
    tampered = encrypted[:-5] + "AAAAA"
    with pytest.raises(Exception):
        decrypt_credential(tampered)


def test_mask_api_key():
    """Verifies key masking preserves only edge characters."""
    key = "abcdefgh12345678ijklmnop98765432"
    masked = mask_api_key(key)
    assert masked.startswith("abcd")
    assert masked.endswith("5432")
    assert "****" in masked
    assert key not in masked


def test_cross_user_isolation_and_idor_prevention(client, db):
    """Verifies that User A's exchange credentials cannot be viewed or accessed by User B."""
    # 1. Provision two distinct test users in DB
    u1_id = str(uuid.uuid4())
    u2_id = str(uuid.uuid4())

    user1 = User(
        id=u1_id,
        email=f"user1_{u1_id[:8]}@test.com",
        username=f"user1_{u1_id[:8]}",
        hashed_password=hash_password("Pass123!"),
        is_active=True
    )
    user2 = User(
        id=u2_id,
        email=f"user2_{u2_id[:8]}@test.com",
        username=f"user2_{u2_id[:8]}",
        hashed_password=hash_password("Pass123!"),
        is_active=True
    )
    db.add(user1)
    db.add(user2)
    db.commit()

    token1 = create_access_token({"sub": user1.id})
    token2 = create_access_token({"sub": user2.id})

    # 2. User 1 creates an encrypted exchange connection in DB
    raw_key = "user1_api_key_1234567890_abcdef"
    raw_sec = "user1_api_secret_1234567890_ghijkl"
    cred = ExchangeCredential(
        id=str(uuid.uuid4()),
        user_id=user1.id,
        exchange="binance_futures",
        label="User 1 Connection",
        encrypted_api_key=encrypt_credential(raw_key),
        encrypted_api_secret=encrypt_credential(raw_sec),
        key_mask=mask_api_key(raw_key),
        testnet=True,
        is_active=True,
        status="CONNECTED"
    )
    db.add(cred)
    db.commit()

    # 3. User 1 queries their connections -> sees their connection
    res1 = client.get("/api/exchange/connections", headers={"Authorization": f"Bearer {token1}"})
    assert res1.status_code == 200
    conns1 = res1.json()
    assert len(conns1) == 1
    assert conns1[0]["id"] == cred.id
    assert conns1[0]["key_mask"] == mask_api_key(raw_key)

    # 4. User 2 queries their connections -> receives empty list (NO LEAKAGE)
    res2 = client.get("/api/exchange/connections", headers={"Authorization": f"Bearer {token2}"})
    assert res2.status_code == 200
    conns2 = res2.json()
    assert len(conns2) == 0

    # 5. User 2 attempts IDOR deletion of User 1's connection -> must fail 404
    del_res = client.delete(f"/api/exchange/connections/{cred.id}", headers={"Authorization": f"Bearer {token2}"})
    assert del_res.status_code == 404

    # Cleanup
    db.delete(cred)
    db.delete(user1)
    db.delete(user2)
    db.commit()


def test_watchlist_cross_user_isolation(client, db):
    """Verifies that user watchlists are strictly isolated per user."""
    u1_id = str(uuid.uuid4())
    u2_id = str(uuid.uuid4())

    user1 = User(id=u1_id, email=f"u1_{u1_id[:6]}@t.com", username=f"u1_{u1_id[:6]}", hashed_password=hash_password("Pass1!"), is_active=True)
    user2 = User(id=u2_id, email=f"u2_{u2_id[:6]}@t.com", username=f"u2_{u2_id[:6]}", hashed_password=hash_password("Pass1!"), is_active=True)
    db.add_all([user1, user2])
    db.commit()

    t1 = create_access_token({"sub": user1.id})
    t2 = create_access_token({"sub": user2.id})

    # User 1 adds ARBUSDT
    client.post("/api/watchlist/ARBUSDT", headers={"Authorization": f"Bearer {t1}"})

    # User 1 has ARBUSDT
    w1 = client.get("/api/watchlist", headers={"Authorization": f"Bearer {t1}"}).json()["symbols"]
    assert "ARBUSDT" in w1

    # User 2 does NOT have ARBUSDT
    w2 = client.get("/api/watchlist", headers={"Authorization": f"Bearer {t2}"}).json()["symbols"]
    assert "ARBUSDT" not in w2

    # Cleanup
    db.query(UserWatchlist).filter(UserWatchlist.user_id.in_([u1_id, u2_id])).delete()
    db.delete(user1)
    db.delete(user2)
    db.commit()


def test_paper_only_execution_boundary():
    """Verifies server-level paper trading enforcement and zero live execution paths."""
    # 1. Trading mode verification
    assert settings.TRADING_MODE.lower() == "paper"
    assert settings.is_paper_trading is True

    # 2. Binance Futures client has ZERO order execution methods
    client = BinanceFuturesClient()
    for forbidden_method in ["place_order", "create_order", "send_order", "cancel_order", "modify_order"]:
        assert not hasattr(client, forbidden_method), f"Live execution method '{forbidden_method}' found on client!"

    # 3. Paper engine maintains simulated balances
    from trading_ai.execution.paper import paper_engine
    assert hasattr(paper_engine, "open_position")
    assert hasattr(paper_engine, "close_position")
    assert paper_engine.cash > 0


def test_rate_limiting_gate():
    """Verifies that rapid login requests from same IP trigger rate limits."""
    ip = "192.0.2.99"
    # Max 5 attempts
    for _ in range(5):
        assert check_rate_limit(f"login:{ip}", max_requests=5, window_seconds=60) is True

    # 6th attempt must be rejected
    assert check_rate_limit(f"login:{ip}", max_requests=5, window_seconds=60) is False
