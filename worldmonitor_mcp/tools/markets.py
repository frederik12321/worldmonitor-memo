"""Markets & economy tools — quotes, indices, macro signals, energy, FRED, rates, ETF."""

from __future__ import annotations

import asyncio

from ..client import _get, _fmt
from ..validation import validate_country, validate_series_id


def register_tools(mcp):

    @mcp.tool()
    async def get_market_snapshot() -> str:
        """Get current market quotes for major indices, commodities, and crypto."""
        markets, commodities, crypto = await asyncio.gather(
            _get("/api/market/v1/list-market-quotes"),
            _get("/api/market/v1/list-commodity-quotes"),
            _get("/api/market/v1/list-crypto-quotes"),
        )
        return _fmt({"markets": markets, "commodities": commodities, "crypto": crypto})

    @mcp.tool()
    async def get_country_stock_index(country_code: str) -> str:
        """Get the primary stock market index for a specific country.

        Args:
            country_code: ISO alpha-2 code (e.g. "DE" for DAX, "JP" for Nikkei).
        """
        cc = validate_country(country_code)
        return _fmt(await _get("/api/market/v1/get-country-stock-index", {"country_code": cc}))

    @mcp.tool()
    async def get_macro_signals() -> str:
        """Get the 7-signal macro dashboard with BUY/CASH verdict."""
        return _fmt(await _get("/api/economic/v1/get-macro-signals"))

    @mcp.tool()
    async def get_energy_prices() -> str:
        """Get current energy commodity prices (oil, gas, coal, electricity)."""
        return _fmt(await _get("/api/economic/v1/get-energy-prices"))

    @mcp.tool()
    async def get_economic_indicators(series_id: str = "UNRATE") -> str:
        """Get Federal Reserve (FRED) economic time series data.

        Args:
            series_id: FRED series ID. Common: "UNRATE", "CPIAUCSL", "GDP",
                       "DFF", "T10Y2Y", "UMCSENT".
        """
        sid = validate_series_id(series_id)
        return _fmt(await _get("/api/economic/v1/get-fred-series", {"series_id": sid}))

    @mcp.tool()
    async def get_central_bank_rates() -> str:
        """Get BIS central bank policy rates for major economies."""
        return _fmt(await _get("/api/economic/v1/get-bis-policy-rates"))

    @mcp.tool()
    async def get_etf_flows() -> str:
        """Get ETF flow data — institutional money movement as a sentiment indicator."""
        return _fmt(await _get("/api/market/v1/list-etf-flows"))
