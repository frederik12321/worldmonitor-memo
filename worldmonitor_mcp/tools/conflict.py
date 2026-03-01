"""Conflict & unrest tools — ACLED events, social unrest, humanitarian."""

from __future__ import annotations

from ..client import _get, _fmt
from ..validation import validate_country


def register_tools(mcp):

    @mcp.tool()
    async def get_conflict_events(country: str | None = None) -> str:
        """Get ACLED armed conflict events (battles, explosions, violence against civilians).

        Args:
            country: Optional ISO alpha-2 code to filter by country.
        """
        params = {}
        if country:
            params["country"] = validate_country(country)
        return _fmt(await _get("/api/conflict/v1/list-acled-events", params))

    @mcp.tool()
    async def get_unrest_events() -> str:
        """Get social unrest events (protests, riots, strikes) with clustering."""
        return _fmt(await _get("/api/unrest/v1/list-unrest-events"))

    @mcp.tool()
    async def get_humanitarian_summary(country_code: str) -> str:
        """Get humanitarian situation summary for a country.

        Args:
            country_code: ISO alpha-2 country code.
        """
        cc = validate_country(country_code)
        return _fmt(await _get("/api/conflict/v1/get-humanitarian-summary", {"country_code": cc}))
