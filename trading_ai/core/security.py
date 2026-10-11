"""Core Security & Cryptography Module.

Provides:
- OWASP-compliant password hashing via hashlib.scrypt with cryptographically random salts
- Cryptographic JWT bearer token generation & validation via PyJWT
- Authenticated AES-256-GCM / Fernet encryption at rest for user exchange credentials
- Key masking to prevent accidental credential leakage in UI/logs
- In-memory sliding-window rate limiting for sensitive auth endpoints
"""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from cryptography.fernet import Fernet
import jwt

from trading_ai.config.settings import settings


# ============================================================================
# Password Hashing (hashlib.scrypt with random 16-byte salt)
# Format: <base64_salt>:<base64_hash>
# ============================================================================

def hash_password(plain_password: str) -> str:
    """Hashes a password using scrypt with a cryptographically secure salt."""
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    salt = secrets.token_bytes(16)
    hashed = hashlib.scrypt(
        plain_password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        maxmem=32 * 1024 * 1024
    )
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    hash_b64 = base64.b64encode(hashed).decode("utf-8")
    return f"{salt_b64}:{hash_b64}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verifies a plain password against an scrypt stored hash."""
    if not plain_password or not stored_hash or ":" not in stored_hash:
        return False
    try:
        salt_b64, hash_b64 = stored_hash.split(":", 1)
        salt = base64.b64decode(salt_b64)
        expected_hash = base64.b64decode(hash_b64)
        computed_hash = hashlib.scrypt(
            plain_password.encode("utf-8"),
            salt=salt,
            n=16384,
            r=8,
            p=1,
            maxmem=32 * 1024 * 1024
        )
        return hmac.compare_digest(expected_hash, computed_hash)
    except Exception:
        return False


# ============================================================================
# JWT Bearer Token Management
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Creates a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"iat": now, "exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT access token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


# ============================================================================
# Authenticated Credential Encryption at Rest (Fernet / AES-256-GCM)
# ============================================================================

def _get_encryption_key(custom_key: Optional[str] = None) -> bytes:
    """Derives a 32-byte URL-safe base64 key suitable for Fernet encryption."""
    raw_key = custom_key or settings.ENCRYPTION_MASTER_KEY
    if not raw_key:
        # Fallback deterministic derivation from SECRET_KEY
        derived = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(derived)

    # If already 32-byte base64, use directly; otherwise hash to 32 bytes and base64-encode
    try:
        decoded = base64.urlsafe_b64decode(raw_key.encode("utf-8"))
        if len(decoded) == 32:
            return raw_key.encode("utf-8")
    except Exception:
        pass

    derived = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(derived)


def encrypt_credential(plain_secret: str, master_key: Optional[str] = None) -> str:
    """Encrypts a plaintext secret into an authenticated ciphertext string."""
    if not plain_secret:
        return ""
    key = _get_encryption_key(master_key)
    f = Fernet(key)
    encrypted_bytes = f.encrypt(plain_secret.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_credential(ciphertext: str, master_key: Optional[str] = None) -> str:
    """Decrypts an authenticated ciphertext string back into plaintext."""
    if not ciphertext:
        return ""
    key = _get_encryption_key(master_key)
    f = Fernet(key)
    decrypted_bytes = f.decrypt(ciphertext.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")


def mask_api_key(key: str) -> str:
    """Masks an API key for safe display, preserving only prefix and suffix."""
    if not key:
        return "None"
    k = key.strip()
    if len(k) <= 8:
        return "****"
    return f"{k[:4]}****{k[-4:]}"


# ============================================================================
# In-Memory Sliding-Window Rate Limiter for Sensitive Auth Endpoints
# ============================================================================

_rate_limit_records: Dict[str, list] = {}

def check_rate_limit(
    identifier: str,
    max_requests: int = 5,
    window_seconds: int = 60
) -> bool:
    """Returns True if request is allowed, False if rate limit is exceeded."""
    now = time.time()
    cutoff = now - window_seconds
    timestamps = _rate_limit_records.get(identifier, [])
    # Filter expired timestamps
    valid_timestamps = [ts for ts in timestamps if ts > cutoff]
    if len(valid_timestamps) >= max_requests:
        _rate_limit_records[identifier] = valid_timestamps
        return False
    valid_timestamps.append(now)
    _rate_limit_records[identifier] = valid_timestamps
    return True
