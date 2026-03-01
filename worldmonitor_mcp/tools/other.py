"""Other tools — prediction markets, displacement data."""

from __future__ import annotations

from ..client import _get, _fmt


def register_tools(mcp):

    @mcp.tool()
    async def get_prediction_markets() -> str:
        """Get Polymarket prediction data for geopolitical and macro events."""
        return _fmt(await _get("/api/prediction/v1/list-prediction-markets"))

    @mcp.tool()
    async def get_displacement_summary() -> str:
        """Get UNHCR global displacement data — refugees, IDPs, asylum seekers."""
        return _fmt(await _get("/api/displacement/v1/get-displacement-summary"))
