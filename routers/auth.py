"""
routers/auth.py — Authentication endpoints: signup, login, refresh, logout, me.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.jwt import create_access_token, create_refresh_token, hash_token
from database import get_db
from models import RefreshToken, User
from schemas import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserProfile,
)

import bcrypt

router = APIRouter(prefix="/auth", tags=["Auth"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def _issue_token_pair(user: User, db: Session) -> TokenResponse:
    """Creates an access + refresh token pair, persists the hashed refresh token."""
    access_token, expires_in = create_access_token(user.id, user.email)
    raw_refresh, expires_at = create_refresh_token()

    db_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=expires_in,
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """Register a new account. Returns access + refresh tokens immediately."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    user = User(
        email=payload.email,
        display_name=payload.display_name,
        hashed_password=_hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_token_pair(user, db)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email + password. Returns access + refresh tokens."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not _verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )
    return _issue_token_pair(user, db)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access token.
    The refresh token itself is not rotated (same token stays valid until expiry/logout).
    """
    token_hash = hash_token(payload.refresh_token)
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,  # noqa: E712
    ).first()

    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or has been revoked.",
        )

    if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
        )

    user = db_token.user
    access_token, expires_in = create_access_token(user.id, user.email)
    return AccessTokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke the provided refresh token. Access tokens expire naturally (15 min)."""
    token_hash = hash_token(payload.refresh_token)
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.user_id == current_user.id,
    ).first()

    if db_token:
        db_token.revoked = True
        db.commit()
    # Silently succeed even if the token wasn't found (idempotent)


@router.get("/me", response_model=UserProfile)
def me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile and daily usage count."""
    return current_user

