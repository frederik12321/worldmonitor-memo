"""Response trimming — control output size to fit within token budgets."""

from __future__ import annotations

import json
from typing import Any

DEFAULT_MAX_CHARS = 8000
COMPOSITE_MAX_CHARS = 16000
DEFAULT_MAX_ITEMS = 50


def strip_empty(obj: Any) -> Any:
    """Recursively remove None values, empty strings, and empty lists from dicts."""
    if isinstance(obj, dict):
        return {
            k: strip_empty(v)
            for k, v in obj.items()
            if v is not None and v != "" and v != []
        }
    if isinstance(obj, list):
        return [strip_empty(item) for item in obj]
    return obj


def trim_response(
    data: Any,
    max_items: int | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> Any:
    """Trim response data to fit within token budgets.

    1. Strip null/empty fields recursively.
    2. If data is a list, cap at max_items.
    3. If serialised result exceeds max_chars, binary-search for the right item count.
    """
    data = strip_empty(data)

    # For dict responses with a known list field, don't trim the outer dict
    if not isinstance(data, list):
        return data

    if max_items is not None:
        data = data[:max_items]

    serialised = json.dumps(data, default=str)
    if len(serialised) <= max_chars:
        return data

    # Binary search for item count that fits
    original_len = len(data)
    lo, hi = 1, len(data)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(json.dumps(data[:mid], default=str)) <= max_chars:
            lo = mid
        else:
            hi = mid - 1
    data = data[:lo]
    data.append({"_truncated": True, "_original_count": original_len, "_returned_count": lo})
    return data


def trim_articles(
    articles: list[dict[str, Any]],
    fields: tuple[str, ...] = ("title", "url", "link", "tone", "date", "published"),
) -> list[dict[str, Any]]:
    """Keep only essential fields from article results to reduce token usage."""
    return [{k: v for k, v in a.items() if k in fields} for a in articles]
