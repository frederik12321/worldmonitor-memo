"""Environment & hazards tools — earthquakes, climate anomalies, wildfires."""

from __future__ import annotations

from ..client import _get, _fmt


def register_tools(mcp):

    @mcp.tool()
    async def get_earthquakes() -> str:
        """Get recent earthquake events with magnitude, location, and depth."""
        return _fmt(await _get("/api/seismology/v1/list-earthquakes"))

    @mcp.tool()
    async def get_climate_anomalies() -> str:
        """Get climate anomalies — unusual temperature and precipitation patterns."""
        return _fmt(await _get("/api/climate/v1/list-climate-anomalies"))

    @mcp.tool()
    async def get_wildfire_detections() -> str:
        """Get NASA FIRMS satellite fire/hotspot detections."""
        return _fmt(await _get("/api/wildfire/v1/list-fire-detections"))
