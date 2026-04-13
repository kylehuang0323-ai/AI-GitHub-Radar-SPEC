"""Local cache and API response storage."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FileCache:
    """Simple file-based JSON cache keyed by string."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = cache_dir / "_index.json"
        self._index: dict[str, str] = {}
        if self._index_file.exists():
            self._index = json.loads(self._index_file.read_text(encoding="utf-8"))

    def _key_to_filename(self, key: str) -> str:
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest()[:16] + ".json"

    def get(self, key: str) -> dict | list | None:
        fname = self._index.get(key)
        if not fname:
            return None
        path = self.cache_dir / fname
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def set(self, key: str, value: dict | list) -> None:
        fname = self._key_to_filename(key)
        path = self.cache_dir / fname
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        self._index[key] = fname
        self._index_file.write_text(json.dumps(self._index, ensure_ascii=False), encoding="utf-8")

    def has(self, key: str) -> bool:
        return key in self._index
