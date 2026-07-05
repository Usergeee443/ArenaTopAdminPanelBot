from __future__ import annotations

import json
from pathlib import Path


class SeenStorage:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._data: dict[str, list[str]] = {
            "refunds": [],
            "withdrawals": [],
        }
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if isinstance(raw, dict):
            self._data["refunds"] = [str(item) for item in raw.get("refunds", [])]
            self._data["withdrawals"] = [
                str(item) for item in raw.get("withdrawals", [])
            ]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def is_seen(self, kind: str, item_id: str) -> bool:
        return item_id in self._data[kind]

    def mark_seen(self, kind: str, item_id: str) -> None:
        if item_id not in self._data[kind]:
            self._data[kind].append(item_id)
            self._save()

    def mark_many_seen(self, kind: str, item_ids: list[str]) -> None:
        changed = False
        for item_id in item_ids:
            if item_id not in self._data[kind]:
                self._data[kind].append(item_id)
                changed = True
        if changed:
            self._save()

    def counts(self) -> dict[str, int]:
        return {
            "refunds": len(self._data["refunds"]),
            "withdrawals": len(self._data["withdrawals"]),
        }
