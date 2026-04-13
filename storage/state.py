"""State persistence for pipeline runs."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class RunState:
    """Track last run date and previously seen repos."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._data: dict = {"last_run_date": "", "seen_repos": []}
        if state_file.exists():
            self._data = json.loads(state_file.read_text(encoding="utf-8"))

    @property
    def last_run_date(self) -> str:
        return self._data.get("last_run_date", "")

    @property
    def seen_repos(self) -> list[str]:
        return self._data.get("seen_repos", [])

    def update(self, run_date: str, repo_names: list[str]) -> None:
        self._data["last_run_date"] = run_date
        # Keep last 500 repos
        existing = set(self._data.get("seen_repos", []))
        existing.update(repo_names)
        self._data["seen_repos"] = list(existing)[-500:]
        self._save()

    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.debug("State saved to %s", self.state_file)
