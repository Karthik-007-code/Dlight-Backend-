"""
auth/jwt.py — JWT creation, decoding, and refresh token hashing utilities.
"""
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "insecure-dev-secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))


def create_access_token(user_id: int, email: str) -> tuple[str, int]:
    """
    Returns (encoded_jwt, expire_seconds).
    Payload: sub=user_id, email, type='access'.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": expire,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, ACCESS_TOKEN_EXPIRE_MINUTES * 60


def create_refresh_token() -> tuple[str, datetime]:
    """
    Generates a cryptographically secure opaque refresh token.
    Returns (raw_token, expires_at_datetime).
    The raw token is given to the client; only its SHA-256 hash is stored.
    """
    raw = secrets.token_urlsafe(64)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return raw, expires_at


def decode_access_token(token: str) -> dict:
    """
    Decodes and validates a JWT access token.
    Raises JWTError on failure.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def hash_token(raw_token: str) -> str:
    """SHA-256 hash — used to store refresh tokens without keeping raw values."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
