"""
WorldMonitor MCP Server

Gives Claude access to WorldMonitor's real-time global intelligence data
(100+ sources) for synthesizing geopolitical, military, economic, and
infrastructure briefings.

This is an independent API client for the WorldMonitor platform
(https://github.com/koala73/worldmonitor) by Elie Habib (AGPL-3.0).
No WorldMonitor source code is included in this project.

Security model (NIST CSF aligned):
  IDENTIFY  — All data flows are documented; only known API paths are callable.
  PROTECT   — Input validation, URL pinning, defused XML parsing, credential isolation.
  DETECT    — Sanitized error reporting; no internal paths or keys in responses.
  RESPOND   — Graceful degradation on API failures; structured error returns.
  RECOVER   — Retry with backoff; per-tool error containment.
"""

from __future__ import annotations

import asyncio
import time as _time
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from worldmonitor_mcp.client import (
    _cache,
    _api_health,
    _fmt,
    _get,
    init_clients,
    close_clients,
)
from worldmonitor_mcp.delta import DeltaTracker
from worldmonitor_mcp.tools import (
    intelligence,
    news,
    conflict,
    military,
    markets,
    supply_chain,
    infrastructure,
    maritime,
    environment,
    other,
    composites,
)

# ---------------------------------------------------------------------------
# Lifespan — manage async HTTP clients
# ---------------------------------------------------------------------------

_server_start = _time.monotonic()


@asynccontextmanager
async def _lifespan(app: FastMCP):
    await init_clients()
    try:
        yield {}
    finally:
        await close_clients()


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "WorldMonitor Intelligence",
    instructions=(
        "You have access to WorldMonitor, a real-time global intelligence platform "
        "aggregating 100+ data sources. Use these tools to pull current geopolitical, "
        "military, economic, and infrastructure data, then synthesize intelligence memos.\n\n"
        "Call tools in parallel when possible to minimise latency. "
        "Use composite tools (get_global_briefing, get_country_dashboard, get_market_pulse) "
        "for comprehensive queries — they fetch multiple endpoints in parallel and are faster "
        "than calling individual tools sequentially."
    ),
    lifespan=_lifespan,
)

# Register all tool modules
for _module in [
    intelligence, news, conflict, military, markets,
    supply_chain, infrastructure, maritime, environment,
    other, composites,
]:
    _module.register_tools(mcp)

# ---------------------------------------------------------------------------
# Server-level tools — cache, health, delta
# ---------------------------------------------------------------------------

_delta = DeltaTracker()


@mcp.tool()
async def get_cache_status() -> str:
    """Get TTL cache status — hit rates, entry count, freshness."""
    return _fmt(_cache.status())


@mcp.tool()
async def get_server_status() -> str:
    """Get WorldMonitor MCP server health — uptime, cache stats, API health."""
    uptime = _time.monotonic() - _server_start
    return _fmt({
        "uptime_seconds": round(uptime, 1),
        "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
        "cache": _cache.status(),
        "api_health": _api_health.status(),
    })


@mcp.tool()
async def get_whats_new() -> str:
    """Check monitored endpoints for changes since last check.

    Returns a summary of which data sources have new data.
    Useful for incremental monitoring between full briefings.
    """
    endpoints = {
        "risk_scores": ("/api/intelligence/v1/get-risk-scores", None),
        "theater_posture": ("/api/military/v1/get-theater-posture", None),
        "conflict_events": ("/api/conflict/v1/list-acled-events", None),
        "unrest_events": ("/api/unrest/v1/list-unrest-events", None),
        "prediction_markets": ("/api/prediction/v1/list-prediction-markets", None),
        "chokepoint_status": ("/api/supply-chain/v1/get-chokepoint-status", None),
    }

    # Fetch all monitored endpoints in parallel
    names = list(endpoints.keys())
    coros = [_get(path, params) for path, params in endpoints.values()]
    results = await asyncio.gather(*coros)

    summary: dict[str, dict[str, bool]] = {}
    for name, data in zip(names, results):
        changed, prev = _delta.update_and_check(f"whats_new:{name}", data)
        summary[name] = {
            "changed": changed,
            "first_observation": prev is None,
        }

    changed_count = sum(
        1 for r in summary.values() if r["changed"] and not r["first_observation"]
    )
    return _fmt({
        "summary": f"{changed_count} endpoint(s) have new data",
        "endpoints": summary,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
