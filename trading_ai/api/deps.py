"""Authentication & Authorization FastAPI Dependencies.

Provides:
- OAuth2 Bearer token extraction
- Database user resolution and token verification
- Optional user resolution for endpoints with public fallback
- Admin / Superuser authorization gate
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from trading_ai.core.security import decode_access_token
from trading_ai.database.models import User
from trading_ai.database.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Validates JWT bearer token and retrieves authenticated User. Fails closed."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or session expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Retrieves authenticated user if valid token is provided; returns None otherwise."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.is_active:
                return user
    except Exception:
        pass
    return None


def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensures authenticated user has administrator privileges."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Administrator access required."
        )
    return current_user
