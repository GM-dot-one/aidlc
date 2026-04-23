"""Thread-safe TTL cache for expensive lookups.

Used to avoid redundant API calls for data that changes infrequently
(e.g. OpenProject types and statuses). The cache is intentionally simple:
one lock, dict-based storage, per-key expiry.
"""

from __future__ import annotations

import threading
import time
from typing import TypeVar

T = TypeVar("T")

_DEFAULT_TTL = 300.0  # 5 minutes


class TTLCache:
    """Thread-safe key→value cache with per-key time-to-live."""

    def __init__(self, ttl: float = _DEFAULT_TTL) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> object | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: object) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
