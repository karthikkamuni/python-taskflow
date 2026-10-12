"""Thin Redis cache wrapper. If Redis is not configured or is down, every
function degrades to a no-op so the API keeps working (just without caching)."""
import json
import logging
from typing import Any, Optional

import redis

from .config import CACHE_TTL_SECONDS, REDIS_URL

logger = logging.getLogger("taskflow.cache")
_client: Optional[redis.Redis] = None


def _get_client() -> Optional[redis.Redis]:
    global _client
    if not REDIS_URL:
        return None
    if _client is None:
        _client = redis.Redis.from_url(
            REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
    return _client


def cache_get(key: str) -> Optional[Any]:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except redis.RedisError as exc:
        logger.warning("cache get failed: %s", exc)
        return None


def cache_set(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value), ex=ttl)
    except redis.RedisError as exc:
        logger.warning("cache set failed: %s", exc)


def cache_delete(*keys: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(*keys)
    except redis.RedisError as exc:
        logger.warning("cache delete failed: %s", exc)


def cache_status() -> str:
    """Return 'disabled', 'up' or 'down' (used by /health)."""
    client = _get_client()
    if client is None:
        return "disabled"
    try:
        client.ping()
        return "up"
    except redis.RedisError:
        return "down"
