"""Military tools — theater posture, flights, fleet report."""

from __future__ import annotations

from ..client import _get, _fmt


def register_tools(mcp):

    @mcp.tool()
    async def get_theater_posture() -> str:
        """Get military posture assessments for all strategic theaters."""
        return _fmt(await _get("/api/military/v1/get-theater-posture"))

    @mcp.tool()
    async def get_military_flights() -> str:
        """Get currently tracked military aircraft flights worldwide."""
        return _fmt(await _get("/api/military/v1/list-military-flights"))

    @mcp.tool()
    async def get_naval_fleet_report() -> str:
        """Get USNI Fleet Tracker report — US Navy carrier strike group deployments."""
        return _fmt(await _get("/api/military/v1/get-usni-fleet-report"))
