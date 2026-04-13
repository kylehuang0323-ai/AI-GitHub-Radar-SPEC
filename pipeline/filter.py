"""Filter pipeline stage: remove noise from candidate repositories."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from config import Config
from models import RepoRecord

logger = logging.getLogger(__name__)


def _is_ai_related(record: RepoRecord, keywords: list[str]) -> bool:
    """Check if the repo is AI-related based on topics, description, or README."""
    searchable = " ".join([
        record.description.lower(),
        " ".join(record.topics),
        record.readme_text[:3000].lower(),
    ])
    return any(kw in searchable for kw in keywords)


def _has_valid_license(record: RepoRecord, allowlist: list[str]) -> bool:
    if not record.license_spdx:
        return False
    return record.license_spdx in allowlist or record.license_spdx == "NOASSERTION"


def _is_recently_active(record: RepoRecord, max_inactive_days: int) -> bool:
    if not record.pushed_at:
        return False
    now = datetime.now(timezone.utc)
    pushed = record.pushed_at if record.pushed_at.tzinfo else record.pushed_at.replace(tzinfo=timezone.utc)
    delta = (now - pushed).days
    return delta <= max_inactive_days


def _has_quality_readme(record: RepoRecord, min_length: int) -> bool:
    return len(record.readme_text.strip()) >= min_length


def filter_records(records: list[RepoRecord], cfg: Config) -> list[RepoRecord]:
    """Apply all filter rules and return passing records."""
    results: list[RepoRecord] = []
    stats = {"total": len(records), "license": 0, "inactive": 0, "readme": 0, "not_ai": 0}

    for rec in records:
        if not _has_valid_license(rec, cfg.license_allowlist):
            stats["license"] += 1
            continue
        if not _is_recently_active(rec, cfg.max_inactive_days):
            stats["inactive"] += 1
            continue
        if not _has_quality_readme(rec, cfg.min_readme_length):
            stats["readme"] += 1
            continue
        if not _is_ai_related(rec, cfg.ai_keywords):
            stats["not_ai"] += 1
            continue
        results.append(rec)

    logger.info(
        "Filter: %d -> %d (dropped: license=%d, inactive=%d, readme=%d, not_ai=%d)",
        stats["total"], len(results),
        stats["license"], stats["inactive"], stats["readme"], stats["not_ai"],
    )
    return results
