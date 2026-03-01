"""Tests for input validation helpers."""

from __future__ import annotations

import pytest

from worldmonitor_mcp.validation import (
    validate_country,
    validate_timespan,
    validate_sort,
    validate_series_id,
    clamp,
)


class TestValidateCountry:
    def test_valid_uppercase(self) -> None:
        assert validate_country("US") == "US"

    def test_valid_lowercase_normalised(self) -> None:
        assert validate_country("ua") == "UA"

    def test_valid_with_whitespace(self) -> None:
        assert validate_country("  cn  ") == "CN"

    def test_three_letter_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_country("USA")

    def test_single_letter_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_country("A")

    def test_digits_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_country("1A")

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_country("")


class TestValidateTimespan:
    @pytest.mark.parametrize("ts", ["15min", "1h", "24h"])
    def test_valid_timespans(self, ts: str) -> None:
        assert validate_timespan(ts) == ts

    def test_invalid_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_timespan("2h")


class TestValidateSort:
    @pytest.mark.parametrize("s", ["DateDesc", "ToneDesc", "ToneAsc", "HybridRel"])
    def test_valid_sorts(self, s: str) -> None:
        assert validate_sort(s) == s

    def test_invalid_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_sort("invalid")


class TestValidateSeriesId:
    def test_valid(self) -> None:
        assert validate_series_id("UNRATE") == "UNRATE"

    def test_normalises_case(self) -> None:
        assert validate_series_id("cpiaucsl") == "CPIAUCSL"

    def test_alphanumeric_underscore(self) -> None:
        assert validate_series_id("T10Y2Y") == "T10Y2Y"

    def test_too_long_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_series_id("A" * 21)

    def test_special_chars_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_series_id("UN-RATE")


class TestClamp:
    def test_within_range(self) -> None:
        assert clamp(5, 1, 10) == 5

    def test_below_min(self) -> None:
        assert clamp(-1, 0, 100) == 0

    def test_above_max(self) -> None:
        assert clamp(500, 0, 100) == 100

    def test_at_boundaries(self) -> None:
        assert clamp(0, 0, 100) == 0
        assert clamp(100, 0, 100) == 100
