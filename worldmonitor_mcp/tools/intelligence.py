"""Intelligence tools — CII risk scores, country briefs, GDELT tensions, article search."""

from __future__ import annotations

from ..client import _get, _fmt
from ..validation import validate_country, validate_timespan, validate_sort, clamp


def register_tools(mcp):  # noqa: C901

    @mcp.tool()
    async def get_risk_scores(region: str | None = None) -> str:
        """Get Country Instability Index (CII) scores and strategic risk assessments.

        Returns CII scores (0-100) per country with components (unrest, conflict,
        security, information), trends, and strategic risk levels.

        Args:
            region: Optional ISO alpha-2 country code to filter (e.g. "UA", "CN").
        """
        params = {}
        if region:
            params["region"] = validate_country(region)
        return _fmt(await _get("/api/intelligence/v1/get-risk-scores", params))

    @mcp.tool()
    async def get_country_intel(country_code: str) -> str:
        """Get an AI-generated intelligence brief for a specific country.

        Args:
            country_code: ISO alpha-2 country code (e.g. "UA", "IR", "CN", "TW").
        """
        cc = validate_country(country_code)
        return _fmt(await _get("/api/intelligence/v1/get-country-intel-brief", {"country_code": cc}))

    @mcp.tool()
    async def get_gdelt_tensions() -> str:
        """Get GDELT inter-state tension pairs and Pentagon Pizza Index (PIZZINT).

        Returns tension scores between country pairs (0-100) with trends,
        plus the PIZZINT indicator for unusual DoD-area activity.
        """
        return _fmt(await _get("/api/intelligence/v1/get-pizzint-status", {"include_gdelt": "true"}))

    @mcp.tool()
    async def search_gdelt_articles(
        query: str,
        timespan: str = "24h",
        max_records: int = 25,
        sort: str = "HybridRel",
    ) -> str:
        """Search GDELT for recent news articles with URLs. Use for sourcing memo citations.

        Args:
            query: Search query (max 200 chars, e.g. "Taiwan military").
            timespan: Time window — "15min", "1h", or "24h".
            max_records: Number of results (1-250).
            sort: Sort order — "DateDesc", "ToneDesc", "ToneAsc", "HybridRel".
        """
        return _fmt(await _get("/api/intelligence/v1/search-gdelt-documents", {
            "query": query[:200],
            "timespan": validate_timespan(timespan),
            "max_records": str(clamp(max_records, 1, 250)),
            "sort": validate_sort(sort),
        }))
