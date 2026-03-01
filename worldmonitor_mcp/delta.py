"""Delta detection — track changes between successive API responses."""

from __future__ import annotations

import hashlib
import json
from typing import Any


class DeltaTracker:
    """Track hashes of previous responses to detect what changed."""

    def __init__(self) -> None:
        self._previous: dict[str, str] = {}  # key → hash
        self._previous_data: dict[str, Any] = {}  # key → last data

    def _hash(self, data: Any) -> str:
        serialised = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialised.encode()).hexdigest()[:16]

    def update_and_check(self, key: str, data: Any) -> tuple[bool, Any | None]:
        """Store current data. Returns (changed, previous_data_or_None)."""
        current_hash = self._hash(data)
        prev_hash = self._previous.get(key)
        prev_data = self._previous_data.get(key)

        self._previous[key] = current_hash
        self._previous_data[key] = data

        if prev_hash is None:
            return True, None  # first observation
        return current_hash != prev_hash, prev_data

    def get_monitored_keys(self) -> list[str]:
        return list(self._previous.keys())

    @staticmethod
    def compute_list_diff(old: list[Any], new: list[Any]) -> dict[str, Any]:
        """Compute a simplified diff for two lists."""
        old_set = {json.dumps(item, sort_keys=True, default=str) for item in old}
        new_set = {json.dumps(item, sort_keys=True, default=str) for item in new}
        added = [json.loads(s) for s in list(new_set - old_set)[:20]]
        removed = [json.loads(s) for s in list(old_set - new_set)[:20]]
        return {
            "added": added,
            "removed": removed,
            "added_count": len(new_set - old_set),
            "removed_count": len(old_set - new_set),
        }

    @staticmethod
    def compute_dict_diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        """Show changed keys between two dicts."""
        changed: dict[str, Any] = {}
        for k in set(old.keys()) | set(new.keys()):
            if old.get(k) != new.get(k):
                changed[k] = {"old": old.get(k), "new": new.get(k)}
        return {"changed_fields": changed}
