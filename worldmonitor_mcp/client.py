"""
HTTP client with NIST CSF security controls.

PROTECT  — URL pinning, credential scoping (no redirects), defused XML.
RESPOND  — Sanitised errors, no internal paths/keys leaked.
RECOVER  — Retry with exponential backoff on 429.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from worldmonitor_mcp.cache import PATH_TTL, TTLCache

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_BASE_URL_RAW = os.environ.get("WORLDMONITOR_BASE_URL", "https://worldmonitor.app")
_API_KEY = os.environ.get("WORLDMONITOR_API_KEY", "")
_TIMEOUT = 30.0
_MAX_RETRIES = 3

_ALLOWED_SCHEMES = {"https"}
_ALLOWED_HOSTS = {
    "worldmonitor.app",
    "tech.worldmonitor.app",
    "finance.worldmonitor.app",
    "happy.worldmonitor.app",
    "localhost",
}

log = logging.getLogger("worldmonitor-mcp")

# ---------------------------------------------------------------------------
# PROTECT — Validate BASE_URL at startup
# ---------------------------------------------------------------------------


def _validate_base_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES and parsed.hostname != "localhost":
        raise ValueError(
            f"WORLDMONITOR_BASE_URL must use HTTPS (got {parsed.scheme}://)"
        )
    if parsed.hostname and parsed.hostname not in _ALLOWED_HOSTS:
        raise ValueError(
            f"WORLDMONITOR_BASE_URL host '{parsed.hostname}' not in allow-list. "
            f"Allowed: {_ALLOWED_HOSTS}"
        )
    return url.rstrip("/")


BASE_URL = _validate_base_url(_BASE_URL_RAW)

# ---------------------------------------------------------------------------
# Cache singleton
# ---------------------------------------------------------------------------

_cache = TTLCache()

# ---------------------------------------------------------------------------
# API health tracker
# ---------------------------------------------------------------------------


class APIHealthTracker:
    """Track success/failure per API endpoint."""

    def __init__(self) -> None:
        self._endpoints: dict[str, dict[str, Any]] = {}

    def record_success(self, path: str) -> None:
        ep = self._endpoints.setdefault(
            path, {"successes": 0, "failures": 0, "last_success": 0.0, "last_failure": 0.0},
        )
        ep["successes"] += 1
        ep["last_success"] = time.monotonic()

    def record_failure(self, path: str) -> None:
        ep = self._endpoints.setdefault(
            path, {"successes": 0, "failures": 0, "last_success": 0.0, "last_failure": 0.0},
        )
        ep["failures"] += 1
        ep["last_failure"] = time.monotonic()

    def status(self) -> dict[str, Any]:
        now = time.monotonic()
        result: dict[str, Any] = {}
        for path, stats in self._endpoints.items():
            total = stats["successes"] + stats["failures"]
            result[path] = {
                "success_rate": round(stats["successes"] / max(total, 1), 3),
                "total_calls": total,
                "last_success_ago": round(now - stats["last_success"], 1) if stats["last_success"] else None,
                "last_failure_ago": round(now - stats["last_failure"], 1) if stats["last_failure"] else None,
            }
        return result


_api_health = APIHealthTracker()

# ---------------------------------------------------------------------------
# PROTECT — HTTP clients with credential scoping
# ---------------------------------------------------------------------------

_headers: dict[str, str] = {}
if _API_KEY:
    _headers["x-api-key"] = _API_KEY

# Module-level holders — initialised eagerly (sync) for now,
# replaced by async clients in lifespan (Step 3).
_client: httpx.AsyncClient | None = None
_rss_client_instance: httpx.AsyncClient | None = None


async def init_clients() -> None:
    """Create async HTTP clients (called from server lifespan)."""
    global _client, _rss_client_instance  # noqa: PLW0603
    _client = httpx.AsyncClient(
        timeout=_TIMEOUT,
        follow_redirects=False,
        headers=_headers,
    )
    _rss_client_instance = httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "WorldMonitor-MCP/1.0"},
    )


async def close_clients() -> None:
    """Close async HTTP clients (called from server lifespan)."""
    global _client, _rss_client_instance  # noqa: PLW0603
    if _client:
        await _client.aclose()
    if _rss_client_instance:
        await _rss_client_instance.aclose()


def get_rss_client() -> httpx.AsyncClient:
    """Get the RSS client (for use in news tools)."""
    assert _rss_client_instance is not None, "Clients not initialised — missing lifespan?"
    return _rss_client_instance


# ---------------------------------------------------------------------------
# RESPOND / RECOVER — Async HTTP request with retry and sanitised errors
# ---------------------------------------------------------------------------


async def _request(method: str, path: str, **kwargs: Any) -> dict:
    """Make an async HTTP request with retry + backoff. Returns parsed JSON or error dict."""
    assert _client is not None, "Clients not initialised — missing lifespan?"
    url = f"{BASE_URL}{path}"
    last_status = 0
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await _client.request(method, url, **kwargs)
            last_status = resp.status_code
            if resp.status_code == 429:
                wait = min(2**attempt * 2, 10)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            _api_health.record_success(path)
            return resp.json()
        except httpx.HTTPStatusError:
            log.warning("API %s %s returned %d", method, path, last_status)
            _api_health.record_failure(path)
            return {"error": f"API returned status {last_status}", "path": path}
        except httpx.RequestError as e:
            log.warning("API %s %s failed: %s", method, path, type(e).__name__)
            _api_health.record_failure(path)
            return {"error": f"Request failed: {type(e).__name__}", "path": path}

    _api_health.record_failure(path)
    return {"error": f"Rate limited after {_MAX_RETRIES} retries", "path": path}


async def _get(path: str, params: dict[str, Any] | None = None) -> dict:
    """GET with transparent TTL caching."""
    ttl = PATH_TTL.get(path, 0)
    if ttl > 0:
        key = _cache.make_key(path, params)
        cached = _cache.get(key)
        if cached is not None:
            return cached
    data = await _request("GET", path, params=params)
    if ttl > 0 and "error" not in data:
        _cache.put(key, data, ttl)  # type: ignore[possibly-undefined]
    return data


async def _post(path: str, body: dict[str, Any]) -> dict:
    return await _request("POST", path, json=body)


def _fmt(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)
