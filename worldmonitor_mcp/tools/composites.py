"""Composite tools — multi-endpoint aggregation with parallel fetching."""

from __future__ import annotations

import asyncio

from ..client import _get, _fmt
from ..trimmer import trim_response, trim_articles, COMPOSITE_MAX_CHARS
from ..validation import validate_country


def register_tools(mcp):

    @mcp.tool()
    async def get_global_briefing() -> str:
        """Get a comprehensive global intelligence briefing in one call.

        Fetches news digest, risk scores, GDELT tensions, theater posture,
        prediction markets, market snapshot, and energy prices in parallel.
        Replaces Phase 1+2 of the memo workflow (12 individual tool calls).
        """
        (
            news, risk, tensions, theater, predictions,
            markets, commodities, crypto, energy,
        ) = await asyncio.gather(
            _get("/api/news/v1/list-feed-digest", {"variant": "full"}),
            _get("/api/intelligence/v1/get-risk-scores"),
            _get("/api/intelligence/v1/get-pizzint-status", {"include_gdelt": "true"}),
            _get("/api/military/v1/get-theater-posture"),
            _get("/api/prediction/v1/list-prediction-markets"),
            _get("/api/market/v1/list-market-quotes"),
            _get("/api/market/v1/list-commodity-quotes"),
            _get("/api/market/v1/list-crypto-quotes"),
            _get("/api/economic/v1/get-energy-prices"),
        )
        return _fmt(trim_response({
            "news_digest": news,
            "risk_scores": risk,
            "gdelt_tensions": tensions,
            "theater_posture": theater,
            "prediction_markets": predictions,
            "market_snapshot": {
                "markets": markets,
                "commodities": commodities,
                "crypto": crypto,
            },
            "energy_prices": energy,
        }, max_chars=COMPOSITE_MAX_CHARS))

    @mcp.tool()
    async def get_country_dashboard(country_code: str) -> str:
        """Get a comprehensive country intelligence dashboard in one call.

        Fetches country intel brief, stock index, conflict events, humanitarian
        summary, and GDELT articles for the country in parallel.
        Replaces Phase 3 of the memo workflow.

        Args:
            country_code: ISO alpha-2 country code (e.g. "UA", "IR", "CN").
        """
        cc = validate_country(country_code)
        intel, stock, conflicts, humanitarian, articles = await asyncio.gather(
            _get("/api/intelligence/v1/get-country-intel-brief", {"country_code": cc}),
            _get("/api/market/v1/get-country-stock-index", {"country_code": cc}),
            _get("/api/conflict/v1/list-acled-events", {"country": cc}),
            _get("/api/conflict/v1/get-humanitarian-summary", {"country_code": cc}),
            _get("/api/intelligence/v1/search-gdelt-documents", {
                "query": cc, "timespan": "24h", "max_records": "15", "sort": "HybridRel",
            }),
        )
        # Trim large list fields
        if isinstance(conflicts, dict) and isinstance(conflicts.get("events"), list):
            conflicts["events"] = trim_response(conflicts["events"], max_items=30)
        if isinstance(articles, dict) and isinstance(articles.get("articles"), list):
            articles["articles"] = trim_articles(articles["articles"])

        return _fmt(trim_response({
            "country": cc,
            "intel_brief": intel,
            "stock_index": stock,
            "conflict_events": conflicts,
            "humanitarian": humanitarian,
            "gdelt_articles": articles,
        }, max_chars=COMPOSITE_MAX_CHARS))

    @mcp.tool()
    async def get_market_pulse() -> str:
        """Get a comprehensive market and economic pulse in one call.

        Fetches market quotes, macro signals, energy prices, shipping rates,
        and ETF flows in parallel.
        """
        markets, commodities, crypto, macro, energy, shipping, etf = await asyncio.gather(
            _get("/api/market/v1/list-market-quotes"),
            _get("/api/market/v1/list-commodity-quotes"),
            _get("/api/market/v1/list-crypto-quotes"),
            _get("/api/economic/v1/get-macro-signals"),
            _get("/api/economic/v1/get-energy-prices"),
            _get("/api/supply-chain/v1/get-shipping-rates"),
            _get("/api/market/v1/list-etf-flows"),
        )
        return _fmt(trim_response({
            "market_snapshot": {
                "markets": markets,
                "commodities": commodities,
                "crypto": crypto,
            },
            "macro_signals": macro,
            "energy_prices": energy,
            "shipping_rates": shipping,
            "etf_flows": etf,
        }, max_chars=COMPOSITE_MAX_CHARS))
