"""Supply chain tools — shipping rates, chokepoints, trade restrictions."""

from __future__ import annotations

from ..client import _get, _fmt


def register_tools(mcp):

    @mcp.tool()
    async def get_shipping_rates() -> str:
        """Get container shipping rate indices. Spikes indicate supply chain stress."""
        return _fmt(await _get("/api/supply-chain/v1/get-shipping-rates"))

    @mcp.tool()
    async def get_chokepoint_status() -> str:
        """Get disruption status for critical maritime chokepoints (Suez, Hormuz, etc.)."""
        return _fmt(await _get("/api/supply-chain/v1/get-chokepoint-status"))

    @mcp.tool()
    async def get_trade_restrictions() -> str:
        """Get current trade restrictions, sanctions, and tariff actions."""
        return _fmt(await _get("/api/trade/v1/get-trade-restrictions"))
