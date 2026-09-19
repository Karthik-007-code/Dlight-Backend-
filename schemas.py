"""
schemas.py — Pydantic v2 request/response models.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ─── Auth ────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    display_name: Optional[str] = Field(None, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expiry


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ─── User ────────────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    id: int
    email: str
    display_name: Optional[str]
    is_active: bool
    created_at: datetime
    requests_today: int

    model_config = {"from_attributes": True}


# ─── Flights ─────────────────────────────────────────────────────────────────

class FlightQueryParams(BaseModel):
    """All optional query params forwarded to AviationStack /v1/flights."""
    flight_iata: Optional[str] = None
    flight_icao: Optional[str] = None
    airline_name: Optional[str] = None
    airline_iata: Optional[str] = None
    airline_icao: Optional[str] = None
    dep_iata: Optional[str] = None
    dep_icao: Optional[str] = None
    arr_iata: Optional[str] = None
    arr_icao: Optional[str] = None
    flight_status: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=100)
    offset: Optional[int] = Field(None, ge=0)


# ─── Errors ──────────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    detail: str
