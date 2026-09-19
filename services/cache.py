"""
services/cache.py — In-memory TTL cache singleton for AviationStack responses.
"""
import os
from cachetools import TTLCache

_TTL = int(os.getenv("CACHE_TTL_SECONDS", 60))
_MAX_SIZE = 512  # max distinct cached queries

# Module-level singleton — shared across all requests in the process
_cache: TTLCache = TTLCache(maxsize=_MAX_SIZE, ttl=_TTL)


def make_cache_key(params: dict) -> str:
    """
    Deterministic cache key from a query-param dict.
    Sorts by key so param order doesn't matter.
    """
    return "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)


def get_cached(key: str):
    """Returns cached value or None if missing/expired."""
    return _cache.get(key)


def set_cache(key: str, value) -> None:
    """Stores a value in the cache under the given key."""
    _cache[key] = value


def cache_info() -> dict:
    """Diagnostic info about the current cache state."""
    return {
        "size": len(_cache),
        "maxsize": _cache.maxsize,
        "ttl_seconds": _cache.ttl,
    }
