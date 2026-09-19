"""
models.py — SQLAlchemy ORM models for User, RefreshToken, and UsageLog.
"""
import hashlib
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Date, ForeignKey,
    Integer, String, JSON
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Rolling daily request counter
    requests_today = Column(Integer, default=0, nullable=False)
    last_request_date = Column(Date, nullable=True)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="refresh_tokens")

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """SHA-256 hash of the raw refresh token — never store the raw value."""
        return hashlib.sha256(raw_token.encode()).hexdigest()


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    query_params = Column(JSON, nullable=True)
    status_code = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="usage_logs")
