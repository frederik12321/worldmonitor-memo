"""Tests for TTLCache."""

from __future__ import annotations

import time

from worldmonitor_mcp.cache import TTLCache


def test_put_and_get(cache: TTLCache) -> None:
    cache.put("k1", {"data": 1}, ttl=60)
    assert cache.get("k1") == {"data": 1}


def test_cache_miss(cache: TTLCache) -> None:
    assert cache.get("nonexistent") is None


def test_ttl_expiry(cache: TTLCache) -> None:
    cache.put("k1", "value", ttl=0.05)
    time.sleep(0.1)
    assert cache.get("k1") is None


def test_make_key_deterministic() -> None:
    k1 = TTLCache.make_key("/api/foo", {"a": "1", "b": "2"})
    k2 = TTLCache.make_key("/api/foo", {"a": "1", "b": "2"})
    assert k1 == k2


def test_make_key_param_order_independent() -> None:
    k1 = TTLCache.make_key("/api/foo", {"a": "1", "b": "2"})
    k2 = TTLCache.make_key("/api/foo", {"b": "2", "a": "1"})
    assert k1 == k2


def test_make_key_different_paths() -> None:
    k1 = TTLCache.make_key("/api/foo")
    k2 = TTLCache.make_key("/api/bar")
    assert k1 != k2


def test_invalidate(cache: TTLCache) -> None:
    cache.put("k1", "value", ttl=60)
    cache.invalidate("k1")
    assert cache.get("k1") is None


def test_clear(cache: TTLCache) -> None:
    cache.put("k1", "a", ttl=60)
    cache.put("k2", "b", ttl=60)
    cache.clear()
    assert cache.get("k1") is None
    assert cache.get("k2") is None


def test_hit_miss_counting(cache: TTLCache) -> None:
    cache.put("k1", "val", ttl=60)
    cache.get("k1")  # hit
    cache.get("k1")  # hit
    cache.get("miss")  # miss
    status = cache.status()
    assert status["hits"] == 2
    assert status["misses"] == 1
    assert status["hit_rate"] == round(2 / 3, 3)


def test_status_structure(cache: TTLCache) -> None:
    cache.put("k1", "val", ttl=300)
    status = cache.status()
    assert "total_entries" in status
    assert "hits" in status
    assert "misses" in status
    assert "hit_rate" in status
    assert "entries" in status
    assert "k1" in status["entries"]
    entry = status["entries"]["k1"]
    assert "age_seconds" in entry
    assert "ttl_seconds" in entry
    assert entry["fresh"] is True
