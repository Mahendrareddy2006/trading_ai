"""Authentication Router.

Features:
- Rate-limited login with generic error messages
- Gated user registration (disabled by default via ALLOW_PUBLIC_SIGNUP=False)
- Secure session tokens via JWT
- User profile and session status endpoints
"""

from datetime import datetime, timezone
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from trading_ai.api.deps import get_current_user
from trading_ai.config.settings import settings
from trading_ai.core.security import (
    check_rate_limit,
    create_access_token,
    hash_password,
    verify_password
)
from trading_ai.database.models import User
from trading_ai.database.session import get_db

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ============================================================================
# Request / Response Schemas
# ============================================================================

class LoginRequest(BaseModel):
    username_or_email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class UserProfileResponse(BaseModel):
    id: str
    email: str
    username: str
    is_superuser: bool
    created_at: str
    last_login: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


# ============================================================================
# Endpoints
# ============================================================================

@auth_router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticates user with username or email and returns JWT bearer token."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"login:{client_ip}:{req.username_or_email.lower().strip()}"

    # Rate Limit: max 5 login attempts per minute
    if not check_rate_limit(rate_limit_key, max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 60 seconds before retrying."
        )

    identifier = req.username_or_email.strip().lower()
    user = db.query(User).filter(
        (User.email.ilike(identifier)) | (User.username.ilike(identifier))
    ).first()

    generic_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials. Please verify your email/username and password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user or not user.is_active:
        raise generic_error

    if not verify_password(req.password, user.hashed_password):
        raise generic_error

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({"sub": user.id, "email": user.email, "role": "admin" if user.is_superuser else "user"})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
    }


@auth_router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user. Strictly gated by settings.ALLOW_PUBLIC_SIGNUP."""
    if not settings.ALLOW_PUBLIC_SIGNUP:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is currently disabled. Contact the system administrator for authorized access."
        )

    email = req.email.strip().lower()
    username = req.username.strip()

    if db.query(User).filter(User.email.ilike(email)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is already registered.")

    if db.query(User).filter(User.username.ilike(username)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already taken.")

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        username=username,
        hashed_password=hash_password(req.password),
        is_active=True,
        is_superuser=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email, "role": "user"})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "last_login": None
        }
    }


@auth_router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns profile for currently authenticated user."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else "",
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }


@auth_router.post("/logout")
def logout():
    """Client-side token disposal endpoint."""
    return {"status": "LOGGED_OUT", "message": "Session ended successfully."}
