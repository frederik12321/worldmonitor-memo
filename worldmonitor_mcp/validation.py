"""Input validation helpers (NIST CSF: PROTECT)."""

from __future__ import annotations

import re

_RE_COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")
_RE_SERIES_ID = re.compile(r"^[A-Z0-9_]{1,20}$")
_VALID_TIMESPANS = {"15min", "1h", "24h"}
_VALID_SORTS = {"DateDesc", "ToneDesc", "ToneAsc", "HybridRel"}
_VALID_FT_SECTIONS = {
    "home", "world", "us", "companies", "tech", "markets", "climate", "opinion",
}


def validate_country(code: str) -> str:
    """Validate and normalise an ISO alpha-2 country code."""
    code = code.strip().upper()
    if not _RE_COUNTRY_CODE.match(code):
        raise ValueError("Invalid country code: must be 2 uppercase letters")
    return code


def validate_timespan(ts: str) -> str:
    if ts not in _VALID_TIMESPANS:
        raise ValueError(f"Invalid timespan: must be one of {_VALID_TIMESPANS}")
    return ts


def validate_sort(s: str) -> str:
    if s not in _VALID_SORTS:
        raise ValueError(f"Invalid sort: must be one of {_VALID_SORTS}")
    return s


def validate_series_id(sid: str) -> str:
    sid = sid.strip().upper()
    if not _RE_SERIES_ID.match(sid):
        raise ValueError("Invalid series_id format")
    return sid


def clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))
