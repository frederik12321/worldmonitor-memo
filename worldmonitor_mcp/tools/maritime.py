"""Maritime tools — vessel tracking, navigational warnings."""

from __future__ import annotations

from ..client import _get, _fmt


def register_tools(mcp):

    @mcp.tool()
    async def get_vessel_snapshot() -> str:
        """Get AIS vessel traffic snapshot including military vessels and disruptions."""
        return _fmt(await _get("/api/maritime/v1/get-vessel-snapshot"))

    @mcp.tool()
    async def get_navigational_warnings() -> str:
        """Get active NGA maritime navigational warnings."""
        return _fmt(await _get("/api/maritime/v1/list-navigational-warnings"))
