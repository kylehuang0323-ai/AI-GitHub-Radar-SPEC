"""Score pipeline stage: compute TrendScore and rank repositories."""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone

from models import RepoRecord

logger = logging.getLogger(__name__)

# Tuning constants
_RECENCY_HALF_LIFE = 14.0   # days
_GROWTH_PROXY_K = 0.01      # fallback growth from stars/age


def _recency_factor(pushed_at: datetime | None) -> float:
    if not pushed_at:
        return 0.1
    now = datetime.now(timezone.utc)
    pushed = pushed_at if pushed_at.tzinfo else pushed_at.replace(tzinfo=timezone.utc)
    days = max((now - pushed).total_seconds() / 86400, 0)
    return math.exp(-days / _RECENCY_HALF_LIFE)


def _activity_factor(record: RepoRecord) -> float:
    """Score based on recent push freshness and issue activity."""
    recency = _recency_factor(record.pushed_at)
    issue_signal = min(record.open_issues_count / 50.0, 1.0)
    return 0.7 * recency + 0.3 * issue_signal


def _readme_quality(text: str) -> float:
    """Heuristic quality score based on length and structure."""
    length = len(text.strip())
    if length < 500:
        return 0.2
    section_count = len(re.findall(r"^#{1,3}\s", text, re.MULTILINE))
    has_install = bool(re.search(r"(install|pip|npm|cargo|getting.started)", text, re.I))
    has_usage = bool(re.search(r"(usage|example|quickstart|getting.started)", text, re.I))
    score = min(length / 5000, 1.0) * 0.4
    score += min(section_count / 8, 1.0) * 0.3
    score += 0.15 * has_install + 0.15 * has_usage
    return score


def _growth_component(record: RepoRecord) -> float:
    """Star growth signal (uses star_growth_7d if available, else proxy)."""
    if record.star_growth_7d > 0:
        return math.log1p(record.star_growth_7d)

    # Proxy: stars / age in days
    if record.created_at:
        created = record.created_at if record.created_at.tzinfo else record.created_at.replace(tzinfo=timezone.utc)
        age_days = max((datetime.now(timezone.utc) - created).days, 1)
        daily_rate = record.stars_total / age_days
        return math.log1p(daily_rate * 7)
    return math.log1p(record.stars_total * _GROWTH_PROXY_K)


def compute_scores(records: list[RepoRecord]) -> list[RepoRecord]:
    """Fill computed metrics and trend_score for each record."""
    for rec in records:
        rec.recency_days = (
            (datetime.now(timezone.utc) - rec.pushed_at.replace(tzinfo=timezone.utc)).days
            if rec.pushed_at else 999
        )
        rec.activity_score = _activity_factor(rec)
        rec.readme_quality_score = _readme_quality(rec.readme_text)

        growth = _growth_component(rec)
        recency = _recency_factor(rec.pushed_at)
        rec.trend_score = growth * recency * rec.activity_score * (0.5 + 0.5 * rec.readme_quality_score)

    records.sort(key=lambda r: r.trend_score, reverse=True)
    logger.info("Scored %d repos. Top: %s (%.3f)", len(records),
                records[0].full_name if records else "N/A",
                records[0].trend_score if records else 0)
    return records
