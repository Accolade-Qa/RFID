from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


class StateStore:
    """Persistent set of successfully marked CSV rows."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._processed: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._processed = set(data.get("processed", []))
        except (OSError, json.JSONDecodeError):
            # A corrupt state file should not silently erase state.
            raise RuntimeError(f"Cannot read state file: {self.path}")

    def contains(self, key: str) -> bool:
        return key in self._processed

    def add(self, key: str) -> None:
        self._processed.add(key)
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps({"processed": sorted(self._processed)}, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.path)
