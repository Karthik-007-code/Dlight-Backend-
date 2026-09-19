"""
services/aviation.py — Async HTTP client wrapper for the AviationStack API.
"""
import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("Api_key")
_BASE_URL = os.getenv("Base_url", "https://api.aviationstack.com/v1/")

# Shared async client — reused across requests for connection pooling
_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()


async def fetch_flights(params: dict) -> dict[str, Any]:
    """
    Calls AviationStack GET /v1/flights.
    Injects the API key automatically; forwards all other params from the caller.
    Raises httpx.HTTPStatusError on non-2xx responses from AviationStack.
    """
    client = await get_client()

    # Remove None values before sending
    clean_params = {k: v for k, v in params.items() if v is not None}
    clean_params["access_key"] = _API_KEY

    url = f"{_BASE_URL.rstrip('/')}/flights"
    response = await client.get(url, params=clean_params)
    response.raise_for_status()
    return response.json()
