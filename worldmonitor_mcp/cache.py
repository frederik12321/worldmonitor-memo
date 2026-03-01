"""In-memory TTL cache — no external dependencies (no Redis)."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

# ---------------------------------------------------------------------------
# TTL tiers (seconds)
# ---------------------------------------------------------------------------

TTL_SLOW = 1800  # 30 min
TTL_MEDIUM = 600  # 10 min
TTL_FAST = 180  # 3 min
TTL_NONE = 0  # no cache

# Map API paths → TTL
PATH_TTL: dict[str, float] = {
    # Slow (30 min)
    "/api/intelligence/v1/get-risk-scores": TTL_SLOW,
    "/api/military/v1/get-theater-posture": TTL_SLOW,
    "/api/displacement/v1/get-displacement-summary": TTL_SLOW,
    "/api/conflict/v1/get-humanitarian-summary": TTL_SLOW,
    "/api/infrastructure/v1/get-cable-health": TTL_SLOW,
    "/api/economic/v1/get-bis-policy-rates": TTL_SLOW,
    # Medium (10 min)
    "/api/news/v1/list-feed-digest": TTL_MEDIUM,
    "/api/conflict/v1/list-acled-events": TTL_MEDIUM,
    "/api/unrest/v1/list-unrest-events": TTL_MEDIUM,
    "/api/prediction/v1/list-prediction-markets": TTL_MEDIUM,
    "/api/supply-chain/v1/get-chokepoint-status": TTL_MEDIUM,
    "/api/trade/v1/get-trade-restrictions": TTL_MEDIUM,
    "/api/cyber/v1/list-cyber-threats": TTL_MEDIUM,
    "/api/infrastructure/v1/list-internet-outages": TTL_MEDIUM,
    "/api/maritime/v1/list-navigational-warnings": TTL_MEDIUM,
    "/api/economic/v1/get-macro-signals": TTL_MEDIUM,
    "/api/economic/v1/get-fred-series": TTL_MEDIUM,
    "/api/seismology/v1/list-earthquakes": TTL_MEDIUM,
    "/api/climate/v1/list-climate-anomalies": TTL_MEDIUM,
    "/api/wildfire/v1/list-fire-detections": TTL_MEDIUM,
    # Fast (3 min)
    "/api/market/v1/list-market-quotes": TTL_FAST,
    "/api/market/v1/list-commodity-quotes": TTL_FAST,
    "/api/market/v1/list-crypto-quotes": TTL_FAST,
    "/api/market/v1/get-country-stock-index": TTL_FAST,
    "/api/market/v1/list-etf-flows": TTL_FAST,
    "/api/economic/v1/get-energy-prices": TTL_FAST,
    "/api/supply-chain/v1/get-shipping-rates": TTL_FAST,
    "/api/military/v1/list-military-flights": TTL_FAST,
    "/api/maritime/v1/get-vessel-snapshot": TTL_FAST,
    # No cache (query-dependent or AI-generated)
    # /api/intelligence/v1/search-gdelt-documents  → TTL_NONE (default)
    # /api/intelligence/v1/get-country-intel-brief  → TTL_NONE (default)
    # /api/intelligence/v1/get-pizzint-status       → TTL_MEDIUM added below
    "/api/intelligence/v1/get-pizzint-status": TTL_MEDIUM,
}


# ---------------------------------------------------------------------------
# TTLCache
# ---------------------------------------------------------------------------


class TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, float, Any]] = {}  # key → (ts, ttl, data)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def make_key(path: str, params: dict[str, Any] | None = None) -> str:
        """Deterministic cache key from path + sorted params."""
        parts = [path]
        if params:
            parts.append(json.dumps(sorted(params.items()), default=str))
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, key: str) -> Any | None:
        """Return cached value if fresh, else None."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            ts, ttl, data = entry
            if time.monotonic() - ts > ttl:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return data

    def put(self, key: str, data: Any, ttl: float) -> None:
        with self._lock:
            self._store[key] = (time.monotonic(), ttl, data)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def status(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            entries = {}
            for key, (ts, ttl, _) in self._store.items():
                age = now - ts
                entries[key] = {
                    "age_seconds": round(age, 1),
                    "ttl_seconds": ttl,
                    "fresh": age <= ttl,
                }
            return {
                "total_entries": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / max(self._hits + self._misses, 1), 3),
                "entries": entries,
            }
