"""Infrastructure & cyber tools — internet outages, cyber threats, submarine cables."""

from __future__ import annotations

from ..client import _get, _fmt


def register_tools(mcp):

    @mcp.tool()
    async def get_internet_outages() -> str:
        """Get current internet outages and disruptions worldwide."""
        return _fmt(await _get("/api/infrastructure/v1/list-internet-outages"))

    @mcp.tool()
    async def get_cyber_threats() -> str:
        """Get current cyber threat indicators (malware, C2 servers, phishing)."""
        return _fmt(await _get("/api/cyber/v1/list-cyber-threats"))

    @mcp.tool()
    async def get_cable_health() -> str:
        """Get submarine cable health status."""
        return _fmt(await _get("/api/infrastructure/v1/get-cable-health"))
