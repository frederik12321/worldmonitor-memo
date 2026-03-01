"""
WorldMonitor MCP Server

Gives Claude access to WorldMonitor's real-time global intelligence data
(100+ sources) for synthesizing geopolitical, military, economic, and
infrastructure briefings.

Security model (NIST CSF aligned):
  IDENTIFY  — All data flows are documented; only known API paths are callable.
  PROTECT   — Input validation, URL pinning, defused XML parsing, credential isolation.
  DETECT    — Sanitized error reporting; no internal paths or keys in responses.
  RESPOND   — Graceful degradation on API failures; structured error returns.
  RECOVER   — Retry with backoff; per-tool error containment.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlparse

import defusedxml.ElementTree as ET
import httpx
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_BASE_URL_RAW = os.environ.get("WORLDMONITOR_BASE_URL", "https://worldmonitor.app")
_API_KEY = os.environ.get("WORLDMONITOR_API_KEY", "")
_TIMEOUT = 30.0
_MAX_RETRIES = 3
_ALLOWED_SCHEMES = {"https"}
_ALLOWED_HOSTS = {
    "worldmonitor.app",
    "tech.worldmonitor.app",
    "finance.worldmonitor.app",
    "happy.worldmonitor.app",
    "localhost",
}

log = logging.getLogger("worldmonitor-mcp")

# ---------------------------------------------------------------------------
# PROTECT — Validate BASE_URL at startup
# ---------------------------------------------------------------------------


def _validate_base_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES and parsed.hostname != "localhost":
        raise ValueError(
            f"WORLDMONITOR_BASE_URL must use HTTPS (got {parsed.scheme}://)"
        )
    if parsed.hostname and parsed.hostname not in _ALLOWED_HOSTS:
        raise ValueError(
            f"WORLDMONITOR_BASE_URL host '{parsed.hostname}' not in allow-list. "
            f"Allowed: {_ALLOWED_HOSTS}"
        )
    return url.rstrip("/")


BASE_URL = _validate_base_url(_BASE_URL_RAW)

# ---------------------------------------------------------------------------
# PROTECT — HTTP client with credential scoping
# ---------------------------------------------------------------------------

_headers: dict[str, str] = {}
if _API_KEY:
    _headers["x-api-key"] = _API_KEY

# Redirects disabled to prevent credential leakage to third-party hosts
_client = httpx.Client(
    timeout=_TIMEOUT,
    follow_redirects=False,
    headers=_headers,
)

_rss_client = httpx.Client(
    timeout=15.0,
    follow_redirects=True,
    headers={"User-Agent": "WorldMonitor-MCP/1.0"},
)

# ---------------------------------------------------------------------------
# PROTECT — Input validation helpers
# ---------------------------------------------------------------------------

_RE_COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")
_RE_SERIES_ID = re.compile(r"^[A-Z0-9_]{1,20}$")
_VALID_TIMESPANS = {"15min", "1h", "24h"}
_VALID_SORTS = {"DateDesc", "ToneDesc", "ToneAsc", "HybridRel"}
_VALID_FT_SECTIONS = {"home", "world", "us", "companies", "tech", "markets", "climate", "opinion"}


def _validate_country(code: str) -> str:
    code = code.strip().upper()
    if not _RE_COUNTRY_CODE.match(code):
        raise ValueError(f"Invalid country code: must be 2 uppercase letters")
    return code


def _validate_timespan(ts: str) -> str:
    if ts not in _VALID_TIMESPANS:
        raise ValueError(f"Invalid timespan: must be one of {_VALID_TIMESPANS}")
    return ts


def _validate_sort(s: str) -> str:
    if s not in _VALID_SORTS:
        raise ValueError(f"Invalid sort: must be one of {_VALID_SORTS}")
    return s


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


# ---------------------------------------------------------------------------
# RESPOND / RECOVER — HTTP request with retry and sanitised errors
# ---------------------------------------------------------------------------


def _request(method: str, path: str, **kwargs: Any) -> dict:
    """Make an HTTP request with retry + backoff. Returns parsed JSON or error dict."""
    url = f"{BASE_URL}{path}"
    last_status = 0
    for attempt in range(_MAX_RETRIES):
        try:
            resp = _client.request(method, url, **kwargs)
            last_status = resp.status_code
            if resp.status_code == 429:
                wait = min(2**attempt * 2, 10)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError:
            log.warning("API %s %s returned %d", method, path, last_status)
            return {"error": f"API returned status {last_status}", "path": path}
        except httpx.RequestError as e:
            log.warning("API %s %s failed: %s", method, path, type(e).__name__)
            return {"error": f"Request failed: {type(e).__name__}", "path": path}

    return {"error": f"Rate limited after {_MAX_RETRIES} retries", "path": path}


def _get(path: str, params: dict[str, Any] | None = None) -> dict:
    return _request("GET", path, params=params)


def _post(path: str, body: dict[str, Any]) -> dict:
    return _request("POST", path, json=body)


def _fmt(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "WorldMonitor Intelligence",
    instructions=(
        "You have access to WorldMonitor, a real-time global intelligence platform "
        "aggregating 100+ data sources. Use these tools to pull current geopolitical, "
        "military, economic, and infrastructure data, then synthesize intelligence memos.\n\n"
        "Call tools in parallel when possible to minimise latency."
    ),
)


# ── Intelligence ──────────────────────────────────────────────────────────


@mcp.tool()
def get_risk_scores(region: str | None = None) -> str:
    """Get Country Instability Index (CII) scores and strategic risk assessments.

    Returns CII scores (0-100) per country with components (unrest, conflict,
    security, information), trends, and strategic risk levels.

    Args:
        region: Optional ISO alpha-2 country code to filter (e.g. "UA", "CN").
    """
    params = {}
    if region:
        params["region"] = _validate_country(region)
    return _fmt(_get("/api/intelligence/v1/get-risk-scores", params))


@mcp.tool()
def get_country_intel(country_code: str) -> str:
    """Get an AI-generated intelligence brief for a specific country.

    Args:
        country_code: ISO alpha-2 country code (e.g. "UA", "IR", "CN", "TW").
    """
    cc = _validate_country(country_code)
    return _fmt(_get("/api/intelligence/v1/get-country-intel-brief", {"country_code": cc}))


@mcp.tool()
def get_gdelt_tensions() -> str:
    """Get GDELT inter-state tension pairs and Pentagon Pizza Index (PIZZINT).

    Returns tension scores between country pairs (0-100) with trends,
    plus the PIZZINT indicator for unusual DoD-area activity.
    """
    return _fmt(_get("/api/intelligence/v1/get-pizzint-status", {"include_gdelt": "true"}))


@mcp.tool()
def search_gdelt_articles(
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
    return _fmt(_get("/api/intelligence/v1/search-gdelt-documents", {
        "query": query[:200],
        "timespan": _validate_timespan(timespan),
        "max_records": str(_clamp(max_records, 1, 250)),
        "sort": _validate_sort(sort),
    }))


# ── News ──────────────────────────────────────────────────────────────────


@mcp.tool()
def get_global_news_digest(variant: str = "full") -> str:
    """Get the current global news digest — all aggregated headlines by category.

    Args:
        variant: "full" (geopolitics), "tech", "finance", or "happy".
    """
    allowed = {"full", "tech", "finance", "happy"}
    v = variant.lower() if variant.lower() in allowed else "full"
    return _fmt(_get("/api/news/v1/list-feed-digest", {"variant": v}))


# ── Conflict & Unrest ─────────────────────────────────────────────────────


@mcp.tool()
def get_conflict_events(country: str | None = None) -> str:
    """Get ACLED armed conflict events (battles, explosions, violence against civilians).

    Args:
        country: Optional ISO alpha-2 code to filter by country.
    """
    params = {}
    if country:
        params["country"] = _validate_country(country)
    return _fmt(_get("/api/conflict/v1/list-acled-events", params))


@mcp.tool()
def get_unrest_events() -> str:
    """Get social unrest events (protests, riots, strikes) with clustering."""
    return _fmt(_get("/api/unrest/v1/list-unrest-events"))


@mcp.tool()
def get_humanitarian_summary(country_code: str) -> str:
    """Get humanitarian situation summary for a country.

    Args:
        country_code: ISO alpha-2 country code.
    """
    cc = _validate_country(country_code)
    return _fmt(_get("/api/conflict/v1/get-humanitarian-summary", {"country_code": cc}))


# ── Military ──────────────────────────────────────────────────────────────


@mcp.tool()
def get_theater_posture() -> str:
    """Get military posture assessments for all strategic theaters."""
    return _fmt(_get("/api/military/v1/get-theater-posture"))


@mcp.tool()
def get_military_flights() -> str:
    """Get currently tracked military aircraft flights worldwide."""
    return _fmt(_get("/api/military/v1/list-military-flights"))


@mcp.tool()
def get_naval_fleet_report() -> str:
    """Get USNI Fleet Tracker report — US Navy carrier strike group deployments."""
    return _fmt(_get("/api/military/v1/get-usni-fleet-report"))


# ── Markets & Economy ─────────────────────────────────────────────────────


@mcp.tool()
def get_market_snapshot() -> str:
    """Get current market quotes for major indices, commodities, and crypto."""
    markets = _get("/api/market/v1/list-market-quotes")
    commodities = _get("/api/market/v1/list-commodity-quotes")
    crypto = _get("/api/market/v1/list-crypto-quotes")
    return _fmt({"markets": markets, "commodities": commodities, "crypto": crypto})


@mcp.tool()
def get_country_stock_index(country_code: str) -> str:
    """Get the primary stock market index for a specific country.

    Args:
        country_code: ISO alpha-2 code (e.g. "DE" for DAX, "JP" for Nikkei).
    """
    cc = _validate_country(country_code)
    return _fmt(_get("/api/market/v1/get-country-stock-index", {"country_code": cc}))


@mcp.tool()
def get_macro_signals() -> str:
    """Get the 7-signal macro dashboard with BUY/CASH verdict."""
    return _fmt(_get("/api/economic/v1/get-macro-signals"))


@mcp.tool()
def get_energy_prices() -> str:
    """Get current energy commodity prices (oil, gas, coal, electricity)."""
    return _fmt(_get("/api/economic/v1/get-energy-prices"))


@mcp.tool()
def get_economic_indicators(series_id: str = "UNRATE") -> str:
    """Get Federal Reserve (FRED) economic time series data.

    Args:
        series_id: FRED series ID. Common: "UNRATE", "CPIAUCSL", "GDP",
                   "DFF", "T10Y2Y", "UMCSENT".
    """
    sid = series_id.strip().upper()
    if not _RE_SERIES_ID.match(sid):
        return _fmt({"error": "Invalid series_id format"})
    return _fmt(_get("/api/economic/v1/get-fred-series", {"series_id": sid}))


@mcp.tool()
def get_central_bank_rates() -> str:
    """Get BIS central bank policy rates for major economies."""
    return _fmt(_get("/api/economic/v1/get-bis-policy-rates"))


# ── Supply Chain ──────────────────────────────────────────────────────────


@mcp.tool()
def get_shipping_rates() -> str:
    """Get container shipping rate indices. Spikes indicate supply chain stress."""
    return _fmt(_get("/api/supply-chain/v1/get-shipping-rates"))


@mcp.tool()
def get_chokepoint_status() -> str:
    """Get disruption status for critical maritime chokepoints (Suez, Hormuz, etc.)."""
    return _fmt(_get("/api/supply-chain/v1/get-chokepoint-status"))


@mcp.tool()
def get_trade_restrictions() -> str:
    """Get current trade restrictions, sanctions, and tariff actions."""
    return _fmt(_get("/api/trade/v1/get-trade-restrictions"))


# ── Infrastructure & Cyber ────────────────────────────────────────────────


@mcp.tool()
def get_internet_outages() -> str:
    """Get current internet outages and disruptions worldwide."""
    return _fmt(_get("/api/infrastructure/v1/list-internet-outages"))


@mcp.tool()
def get_cyber_threats() -> str:
    """Get current cyber threat indicators (malware, C2 servers, phishing)."""
    return _fmt(_get("/api/cyber/v1/list-cyber-threats"))


@mcp.tool()
def get_cable_health() -> str:
    """Get submarine cable health status."""
    return _fmt(_get("/api/infrastructure/v1/get-cable-health"))


# ── Prediction Markets ────────────────────────────────────────────────────


@mcp.tool()
def get_prediction_markets() -> str:
    """Get Polymarket prediction data for geopolitical and macro events."""
    return _fmt(_get("/api/prediction/v1/list-prediction-markets"))


# ── Maritime ──────────────────────────────────────────────────────────────


@mcp.tool()
def get_vessel_snapshot() -> str:
    """Get AIS vessel traffic snapshot including military vessels and disruptions."""
    return _fmt(_get("/api/maritime/v1/get-vessel-snapshot"))


@mcp.tool()
def get_navigational_warnings() -> str:
    """Get active NGA maritime navigational warnings."""
    return _fmt(_get("/api/maritime/v1/list-navigational-warnings"))


# ── Natural Hazards ───────────────────────────────────────────────────────


@mcp.tool()
def get_earthquakes() -> str:
    """Get recent earthquake events with magnitude, location, and depth."""
    return _fmt(_get("/api/seismology/v1/list-earthquakes"))


@mcp.tool()
def get_climate_anomalies() -> str:
    """Get climate anomalies — unusual temperature and precipitation patterns."""
    return _fmt(_get("/api/climate/v1/list-climate-anomalies"))


@mcp.tool()
def get_wildfire_detections() -> str:
    """Get NASA FIRMS satellite fire/hotspot detections."""
    return _fmt(_get("/api/wildfire/v1/list-fire-detections"))


# ── Displacement ──────────────────────────────────────────────────────────


@mcp.tool()
def get_displacement_summary() -> str:
    """Get UNHCR global displacement data — refugees, IDPs, asylum seekers."""
    return _fmt(_get("/api/displacement/v1/get-displacement-summary"))


# ── Financial Stress ──────────────────────────────────────────────────────


@mcp.tool()
def get_etf_flows() -> str:
    """Get ETF flow data — institutional money movement as a sentiment indicator."""
    return _fmt(_get("/api/market/v1/list-etf-flows"))


# ── RSS Feeds (direct) ───────────────────────────────────────────────────

_FT_FEEDS: dict[str, str] = {
    "home": "https://www.ft.com/rss/home",
    "world": "https://www.ft.com/world?format=rss",
    "us": "https://www.ft.com/world/us?format=rss",
    "companies": "https://www.ft.com/companies?format=rss",
    "tech": "https://www.ft.com/technology?format=rss",
    "markets": "https://www.ft.com/markets?format=rss",
    "climate": "https://www.ft.com/climate-capital?format=rss",
    "opinion": "https://www.ft.com/opinion?format=rss",
}


def _parse_rss(xml_text: str) -> list[dict[str, str]]:
    """Parse RSS 2.0 XML into article dicts. Uses defusedxml to prevent XXE/bombs."""
    items: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for item in root.iter("item"):
        entry: dict[str, str] = {}
        for tag, key in [("title", "title"), ("link", "link"),
                         ("description", "description"), ("pubDate", "published"),
                         ("category", "category")]:
            el = item.find(tag)
            if el is not None and el.text:
                entry[key] = el.text.strip()
        if entry.get("title"):
            items.append(entry)
    return items


@mcp.tool()
def get_ft_news(section: str = "home") -> str:
    """Get latest Financial Times headlines with links.

    Args:
        section: FT section — "home", "world", "us", "companies",
                 "tech", "markets", "climate", "opinion".
    """
    section = section.lower() if section.lower() in _VALID_FT_SECTIONS else "home"
    feed_url = _FT_FEEDS[section]
    try:
        resp = _rss_client.get(feed_url)
        resp.raise_for_status()
        articles = _parse_rss(resp.text)
        return _fmt({"section": section, "count": len(articles), "articles": articles})
    except httpx.HTTPError:
        return _fmt({"error": f"FT {section} feed unavailable", "section": section})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
