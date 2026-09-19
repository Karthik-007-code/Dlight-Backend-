"""
middleware/rate_limit.py — slowapi IP rate limiter + per-user daily request limit dependency.
"""
import os
from datetime import date, datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import User

# ─── IP Rate Limiter (slowapi) ────────────────────────────────────────────────

IP_RATE_LIMIT = os.getenv("IP_RATE_LIMIT", "30/minute")

limiter = Limiter(key_func=get_remote_address, default_limits=[IP_RATE_LIMIT])

# ─── Per-User Daily Limit ─────────────────────────────────────────────────────

USER_DAILY_LIMIT = int(os.getenv("USER_DAILY_LIMIT", 200))


def check_user_daily_limit(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that:
      1. Resets the user's daily counter if last_request_date is not today (UTC).
      2. Checks whether the user has exceeded USER_DAILY_LIMIT requests today.
      3. Increments the counter on every call.
    Returns the current user so downstream routes can use it.
    """
    today = date.today()

    if current_user.last_request_date != today:
        # New day — reset counter
        current_user.requests_today = 0
        current_user.last_request_date = today

    if current_user.requests_today >= USER_DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily request limit of {USER_DAILY_LIMIT} reached. Resets at midnight UTC.",
            headers={"X-RateLimit-Reset": "midnight UTC"},
        )

    current_user.requests_today += 1
    db.commit()

    return current_user
