"""Tiny in-process TTL cache (demo / interview talking point — not Redis)."""
from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}


def cache_get(key: str):
    now = time.monotonic()
    with _lock:
        item = _store.get(key)
        if not item:
            return None
        expires, value = item
        if expires < now:
            _store.pop(key, None)
            return None
        return value


def cache_set(key: str, value: Any, ttl_seconds: float = 15.0) -> None:
    with _lock:
        _store[key] = (time.monotonic() + ttl_seconds, value)


def cache_invalidate(*keys: str) -> None:
    with _lock:
        if not keys:
            _store.clear()
            return
        for k in keys:
            _store.pop(k, None)


STATS_CACHE_KEY = "admin:dashboard_stats"
