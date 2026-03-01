"""Tests for delta detection."""

from __future__ import annotations

from worldmonitor_mcp.delta import DeltaTracker


class TestUpdateAndCheck:
    def test_first_observation_is_changed(self, delta: DeltaTracker) -> None:
        changed, prev = delta.update_and_check("key1", {"score": 42})
        assert changed is True
        assert prev is None

    def test_same_data_not_changed(self, delta: DeltaTracker) -> None:
        delta.update_and_check("key1", {"score": 42})
        changed, prev = delta.update_and_check("key1", {"score": 42})
        assert changed is False
        assert prev == {"score": 42}

    def test_different_data_is_changed(self, delta: DeltaTracker) -> None:
        delta.update_and_check("key1", {"score": 42})
        changed, prev = delta.update_and_check("key1", {"score": 99})
        assert changed is True
        assert prev == {"score": 42}

    def test_independent_keys(self, delta: DeltaTracker) -> None:
        delta.update_and_check("a", {"x": 1})
        delta.update_and_check("b", {"x": 2})
        changed_a, _ = delta.update_and_check("a", {"x": 1})
        changed_b, _ = delta.update_and_check("b", {"x": 99})
        assert changed_a is False
        assert changed_b is True

    def test_get_monitored_keys(self, delta: DeltaTracker) -> None:
        delta.update_and_check("alpha", {})
        delta.update_and_check("beta", {})
        keys = delta.get_monitored_keys()
        assert set(keys) == {"alpha", "beta"}


class TestListDiff:
    def test_added_items(self) -> None:
        old = [{"id": 1}, {"id": 2}]
        new = [{"id": 1}, {"id": 2}, {"id": 3}]
        diff = DeltaTracker.compute_list_diff(old, new)
        assert diff["added_count"] == 1
        assert diff["removed_count"] == 0

    def test_removed_items(self) -> None:
        old = [{"id": 1}, {"id": 2}]
        new = [{"id": 1}]
        diff = DeltaTracker.compute_list_diff(old, new)
        assert diff["added_count"] == 0
        assert diff["removed_count"] == 1

    def test_no_changes(self) -> None:
        data = [{"id": 1}]
        diff = DeltaTracker.compute_list_diff(data, data)
        assert diff["added_count"] == 0
        assert diff["removed_count"] == 0


class TestDictDiff:
    def test_changed_fields(self) -> None:
        old = {"a": 1, "b": 2}
        new = {"a": 1, "b": 99}
        diff = DeltaTracker.compute_dict_diff(old, new)
        assert "b" in diff["changed_fields"]
        assert diff["changed_fields"]["b"] == {"old": 2, "new": 99}

    def test_no_changes(self) -> None:
        data = {"a": 1}
        diff = DeltaTracker.compute_dict_diff(data, data)
        assert diff["changed_fields"] == {}
