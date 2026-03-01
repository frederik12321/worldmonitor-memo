"""News tools — global news digest and Financial Times RSS feeds."""

from __future__ import annotations

import defusedxml.ElementTree as ET
import httpx

from ..client import _get, _fmt, get_rss_client
from ..validation import _VALID_FT_SECTIONS

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
        for tag, key in [
            ("title", "title"), ("link", "link"),
            ("description", "description"), ("pubDate", "published"),
            ("category", "category"),
        ]:
            el = item.find(tag)
            if el is not None and el.text:
                entry[key] = el.text.strip()
        if entry.get("title"):
            items.append(entry)
    return items


def register_tools(mcp):

    @mcp.tool()
    async def get_global_news_digest(variant: str = "full") -> str:
        """Get the current global news digest — all aggregated headlines by category.

        Args:
            variant: "full" (geopolitics), "tech", "finance", or "happy".
        """
        allowed = {"full", "tech", "finance", "happy"}
        v = variant.lower() if variant.lower() in allowed else "full"
        return _fmt(await _get("/api/news/v1/list-feed-digest", {"variant": v}))

    @mcp.tool()
    async def get_ft_news(section: str = "home") -> str:
        """Get Financial Times headlines via public RSS. Coverage varies by section.

        Args:
            section: FT section — "home", "world", "us", "companies",
                     "tech", "markets", "climate", "opinion".
        """
        section = section.lower() if section.lower() in _VALID_FT_SECTIONS else "home"
        feed_url = _FT_FEEDS[section]
        try:
            rss_client = get_rss_client()
            resp = await rss_client.get(feed_url)
            resp.raise_for_status()
            articles = _parse_rss(resp.text)
            return _fmt({"section": section, "count": len(articles), "articles": articles})
        except httpx.HTTPError:
            return _fmt({"error": f"FT {section} feed unavailable", "section": section})
