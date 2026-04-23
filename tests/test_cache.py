"""Tests for the TTL cache module."""

from __future__ import annotations

import time
from unittest.mock import patch

from aidlc.cache import TTLCache


class TestTTLCache:
    def test_set_and_get(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.set("key", [1, 2, 3])
        assert cache.get("key") == [1, 2, 3]

    def test_returns_none_for_missing_key(self) -> None:
        cache = TTLCache(ttl=60.0)
        assert cache.get("missing") is None

    def test_expires_after_ttl(self) -> None:
        cache = TTLCache(ttl=0.5)
        cache.set("key", "value")
        assert cache.get("key") == "value"
        time.sleep(0.6)
        assert cache.get("key") is None

    def test_invalidate_removes_key(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.set("key", "value")
        cache.invalidate("key")
        assert cache.get("key") is None

    def test_invalidate_nonexistent_key_is_noop(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.invalidate("nope")

    def test_clear_removes_all_keys(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_overwrite_resets_ttl(self) -> None:
        base_time = 1000.0
        with patch("aidlc.cache.time.monotonic", side_effect=[base_time, base_time + 10.0]):
            cache = TTLCache(ttl=5.0)
            cache.set("key", "old")
            cache.set("key", "new")

        with patch("aidlc.cache.time.monotonic", return_value=base_time + 8.0):
            assert cache.get("key") == "new"
