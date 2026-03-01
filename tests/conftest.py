"""Shared test fixtures."""

from __future__ import annotations

import pytest

from worldmonitor_mcp.cache import TTLCache
from worldmonitor_mcp.delta import DeltaTracker


@pytest.fixture
def cache() -> TTLCache:
    return TTLCache()


@pytest.fixture
def delta() -> DeltaTracker:
    return DeltaTracker()
