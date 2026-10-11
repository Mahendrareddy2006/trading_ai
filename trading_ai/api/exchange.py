"""Exchange Connections Router.

Provides:
- User-supplied read-only exchange credential storage with AES-256-GCM / Fernet encryption at rest
- Per-user scoping and strict IDOR prevention
- Instant read-only validation against official Binance USD(S)-M Futures API
- Credential masking and explicit purge/disconnect
- Connection status tracking (NOT_CONNECTED, CONNECTED, AUTH_FAILED)
"""

from datetime import datetime, timezone
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from trading_ai.api.deps import get_current_user
from trading_ai.core.security import (
    decrypt_credential,
    encrypt_credential,
    mask_api_key
)
from trading_ai.database.models import ExchangeCredential, User
from trading_ai.database.session import get_db
from trading_ai.execution.binance_client import BinanceFuturesClient

exchange_router = APIRouter(prefix="/api/exchange", tags=["Exchange Connections"])


# ============================================================================
# Schemas
# ============================================================================

class ConnectExchangeRequest(BaseModel):
    exchange: str = Field(default="binance_futures", description="Target exchange identifier")
    label: Optional[str] = Field(default="Binance USD(S)-M Futures", max_length=50)
    api_key: str = Field(..., min_length=16, max_length=128)
    api_secret: str = Field(..., min_length=16, max_length=128)
    testnet: bool = Field(default=False)


class ExchangeConnectionResponse(BaseModel):
    id: str
    exchange: str
    label: str
    key_mask: str
    testnet: bool
    is_active: bool
    status: str
    last_error: Optional[str] = None
    last_synced_at: Optional[str] = None
    created_at: str


# ============================================================================
# Endpoints
# ============================================================================

@exchange_router.get("/connections", response_model=List[ExchangeConnectionResponse])
def list_user_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all exchange connections owned by the authenticated user. Credentials remain masked."""
    creds = db.query(ExchangeCredential).filter(
        ExchangeCredential.user_id == current_user.id
    ).order_by(ExchangeCredential.created_at.desc()).all()

    return [
        {
            "id": c.id,
            "exchange": c.exchange,
            "label": c.label,
            "key_mask": c.key_mask,
            "testnet": c.testnet,
            "is_active": c.is_active,
            "status": c.status,
            "last_error": c.last_error,
            "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else ""
        }
        for c in creds
    ]


@exchange_router.post("/connect", response_model=ExchangeConnectionResponse)
def connect_exchange(
    req: ConnectExchangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tests read-only connection, encrypts credentials with AES-GCM at rest, and saves under current user."""
    clean_key = req.api_key.strip()
    clean_secret = req.api_secret.strip()

    # Reject placeholder strings
    if "your_" in clean_key.lower() or "your_" in clean_secret.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Placeholder credentials detected. Please enter your actual read-only Binance API key and secret."
        )

    # 1. Test connection against Binance Futures using in-memory client
    temp_client = BinanceFuturesClient(
        api_key=clean_key,
        api_secret=clean_secret,
        testnet=req.testnet
    )

    summary, err = temp_client.get_account_summary()
    conn_status = "CONNECTED" if not err else "AUTH_FAILED"
    error_detail = err if err else None

    # 2. Encrypt credentials at rest
    enc_key = encrypt_credential(clean_key)
    enc_secret = encrypt_credential(clean_secret)
    key_mask = mask_api_key(clean_key)

    # 3. Save into database scoped to current user
    # Deactivate existing active connections of the same exchange type for this user
    db.query(ExchangeCredential).filter(
        ExchangeCredential.user_id == current_user.id,
        ExchangeCredential.exchange == req.exchange
    ).update({"is_active": False})

    new_cred = ExchangeCredential(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        exchange=req.exchange,
        label=req.label or "Binance USD(S)-M Futures",
        encrypted_api_key=enc_key,
        encrypted_api_secret=enc_secret,
        key_mask=key_mask,
        testnet=req.testnet,
        is_active=True,
        status=conn_status,
        last_error=error_detail,
        last_synced_at=datetime.now(timezone.utc) if conn_status == "CONNECTED" else None
    )
    db.add(new_cred)
    db.commit()
    db.refresh(new_cred)

    return {
        "id": new_cred.id,
        "exchange": new_cred.exchange,
        "label": new_cred.label,
        "key_mask": new_cred.key_mask,
        "testnet": new_cred.testnet,
        "is_active": new_cred.is_active,
        "status": new_cred.status,
        "last_error": new_cred.last_error,
        "last_synced_at": new_cred.last_synced_at.isoformat() if new_cred.last_synced_at else None,
        "created_at": new_cred.created_at.isoformat() if new_cred.created_at else ""
    }


@exchange_router.delete("/connections/{connection_id}")
def delete_exchange_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently purges saved credentials. Scoped strictly to current_user.id (prevents IDOR)."""
    cred = db.query(ExchangeCredential).filter(
        ExchangeCredential.id == connection_id,
        ExchangeCredential.user_id == current_user.id
    ).first()

    if not cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exchange connection not found or does not belong to your account."
        )

    db.delete(cred)
    db.commit()
    return {"status": "DELETED", "message": "Exchange connection and encrypted credentials purged successfully."}


@exchange_router.post("/connections/{connection_id}/sync", response_model=ExchangeConnectionResponse)
def sync_exchange_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Re-verifies connection and synchronizes account status."""
    cred = db.query(ExchangeCredential).filter(
        ExchangeCredential.id == connection_id,
        ExchangeCredential.user_id == current_user.id
    ).first()

    if not cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exchange connection not found."
        )

    # Decrypt in memory
    raw_key = decrypt_credential(cred.encrypted_api_key)
    raw_secret = decrypt_credential(cred.encrypted_api_secret)

    temp_client = BinanceFuturesClient(
        api_key=raw_key,
        api_secret=raw_secret,
        testnet=cred.testnet
    )

    summary, err = temp_client.get_account_summary()
    cred.status = "CONNECTED" if not err else "AUTH_FAILED"
    cred.last_error = err
    if not err:
        cred.last_synced_at = datetime.now(timezone.utc)
    cred.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "id": cred.id,
        "exchange": cred.exchange,
        "label": cred.label,
        "key_mask": cred.key_mask,
        "testnet": cred.testnet,
        "is_active": cred.is_active,
        "status": cred.status,
        "last_error": cred.last_error,
        "last_synced_at": cred.last_synced_at.isoformat() if cred.last_synced_at else None,
        "created_at": cred.created_at.isoformat() if cred.created_at else ""
    }
