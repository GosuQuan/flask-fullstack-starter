"""Redis helper with graceful degrade when down."""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)
_client = None
_force_down = False  # chaos: simulate Redis outage


def set_force_down(flag: bool) -> None:
    global _force_down
    _force_down = flag


def get_redis():
    global _client
    if _force_down:
        return None
    if _client is not None:
        return _client
    url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    try:
        import redis

        c = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.5)
        c.ping()
        _client = c
        return _client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable, degrade to DB: %s", exc)
        _client = None
        return None


def cache_get(key: str) -> Optional[str]:
    r = get_redis()
    if not r:
        return None
    try:
        return r.get(key)
    except Exception:
        return None


def cache_set(key: str, value: str, ttl: int = 30) -> bool:
    r = get_redis()
    if not r:
        return False
    try:
        r.setex(key, ttl, value)
        return True
    except Exception:
        return False


def cache_delete(*keys: str) -> None:
    r = get_redis()
    if not r or not keys:
        return
    try:
        r.delete(*keys)
    except Exception:
        pass


def cache_delete_pattern(pattern: str) -> None:
    r = get_redis()
    if not r:
        return
    try:
        for k in r.scan_iter(match=pattern, count=100):
            r.delete(k)
    except Exception:
        pass


def try_set_nx(key: str, value: str, ttl: int = 60) -> bool:
    """Idempotency lock: True if we acquired it."""
    r = get_redis()
    if not r:
        # Without Redis, allow through (caller still has DB transaction).
        return True
    try:
        return bool(r.set(key, value, nx=True, ex=ttl))
    except Exception:
        return True
