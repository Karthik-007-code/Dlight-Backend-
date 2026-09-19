"""
routers/flights.py — GET /v1/flights proxy endpoint.

Flow:
  1. Validate JWT (get_current_user via check_user_daily_limit)
  2. Check + enforce user daily limit
  3. Check in-memory cache (TTL 60s)
  4. If cache miss: call AviationStack, store result in cache
  5. Log usage to DB
  6. Return response
"""
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from database import get_db
from middleware.rate_limit import check_user_daily_limit, limiter
from models import UsageLog, User
from services.aviation import fetch_flights
from services.cache import get_cached, make_cache_key, set_cache

router = APIRouter(prefix="/v1", tags=["Flights"])


@router.get("/flights")
@limiter.limit("30/minute")
async def get_flights(
    request: Request,  # required by slowapi
    # ── AviationStack query params ──────────────────────────────────────────
    flight_iata: Optional[str] = Query(None),
    flight_icao: Optional[str] = Query(None),
    airline_name: Optional[str] = Query(None),
    airline_iata: Optional[str] = Query(None),
    airline_icao: Optional[str] = Query(None),
    dep_iata: Optional[str] = Query(None),
    dep_icao: Optional[str] = Query(None),
    arr_iata: Optional[str] = Query(None),
    arr_icao: Optional[str] = Query(None),
    flight_status: Optional[str] = Query(None, description="scheduled|active|landed|cancelled|incident|diverted"),
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: Optional[int] = Query(None, ge=0),
    # ── Auth + rate limit ────────────────────────────────────────────────────
    current_user: User = Depends(check_user_daily_limit),
    db: Session = Depends(get_db),
):
    """
    Proxy real-time flight data from AviationStack.

    - **Requires**: Bearer JWT in `Authorization` header.
    - **Rate limited**: 30 req/min per IP · 200 req/day per user.
    - **Cached**: Identical queries are cached for 60 seconds.
    """
    params = {
        "flight_iata": flight_iata,
        "flight_icao": flight_icao,
        "airline_name": airline_name,
        "airline_iata": airline_iata,
        "airline_icao": airline_icao,
        "dep_iata": dep_iata,
        "dep_icao": dep_icao,
        "arr_iata": arr_iata,
        "arr_icao": arr_icao,
        "flight_status": flight_status,
        "limit": limit,
        "offset": offset,
    }

    # ── Cache check ──────────────────────────────────────────────────────────
    cache_key = make_cache_key(params)
    cached = get_cached(cache_key)
    if cached is not None:
        _log_usage(db, current_user, request, params, status_code=200)
        return cached

    # ── Call AviationStack ───────────────────────────────────────────────────
    try:
        data = await fetch_flights(params)
    except httpx.HTTPStatusError as exc:
        _log_usage(db, current_user, request, params, status_code=exc.response.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AviationStack returned {exc.response.status_code}: {exc.response.text[:200]}",
        )
    except httpx.RequestError as exc:
        _log_usage(db, current_user, request, params, status_code=503)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach AviationStack: {str(exc)}",
        )

    # ── Store in cache ───────────────────────────────────────────────────────
    set_cache(cache_key, data)
    _log_usage(db, current_user, request, params, status_code=200)

    return data


# ─── Internal ─────────────────────────────────────────────────────────────────

def _log_usage(
    db: Session,
    user: User,
    request: Request,
    params: dict,
    status_code: int,
) -> None:
    """Write a usage log entry to the database (best-effort, never raises)."""
    try:
        log = UsageLog(
            user_id=user.id,
            ip_address=request.client.host if request.client else "unknown",
            endpoint="/v1/flights",
            query_params={k: v for k, v in params.items() if v is not None},
            status_code=status_code,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()  # Never let logging failures break the response
