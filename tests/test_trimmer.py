"""Tests for response trimming."""

from __future__ import annotations

import json

from worldmonitor_mcp.trimmer import strip_empty, trim_response, trim_articles


class TestStripEmpty:
    def test_removes_none(self) -> None:
        assert strip_empty({"a": None, "b": 1}) == {"b": 1}

    def test_removes_empty_strings(self) -> None:
        assert strip_empty({"a": "", "b": "x"}) == {"b": "x"}

    def test_removes_empty_lists(self) -> None:
        assert strip_empty({"a": [], "b": [1]}) == {"b": [1]}

    def test_recursive(self) -> None:
        data = {"a": {"b": None, "c": "ok"}, "d": ""}
        assert strip_empty(data) == {"a": {"c": "ok"}}

    def test_preserves_zero(self) -> None:
        assert strip_empty({"a": 0}) == {"a": 0}

    def test_preserves_false(self) -> None:
        assert strip_empty({"a": False}) == {"a": False}


class TestTrimResponse:
    def test_list_max_items(self) -> None:
        data = list(range(100))
        result = trim_response(data, max_items=10)
        assert len(result) == 10

    def test_dict_passthrough(self) -> None:
        data = {"key": "value", "empty": None}
        result = trim_response(data)
        assert result == {"key": "value"}

    def test_max_chars_truncation(self) -> None:
        # Create a large list that exceeds 8000 chars
        data = [{"title": f"Item {i}", "description": "x" * 200} for i in range(100)]
        result = trim_response(data, max_chars=2000)
        serialised = json.dumps(result, default=str)
        # The last item is the truncation notice
        assert result[-1].get("_truncated") is True
        # Should be under budget (plus truncation notice)
        assert len(serialised) < 3000  # some overhead from notice

    def test_small_list_not_truncated(self) -> None:
        data = [{"a": 1}, {"a": 2}]
        result = trim_response(data)
        assert result == [{"a": 1}, {"a": 2}]


class TestTrimArticles:
    def test_keeps_essential_fields(self) -> None:
        articles = [
            {"title": "A", "url": "http://a", "tone": 5.0, "extra": "drop", "huge": "x" * 1000}
        ]
        result = trim_articles(articles)
        assert result == [{"title": "A", "url": "http://a", "tone": 5.0}]

    def test_empty_list(self) -> None:
        assert trim_articles([]) == []

    def test_preserves_link_field(self) -> None:
        articles = [{"title": "B", "link": "http://b", "foo": "bar"}]
        result = trim_articles(articles)
        assert result == [{"title": "B", "link": "http://b"}]
