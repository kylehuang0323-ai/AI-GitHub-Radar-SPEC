"""Collect pipeline stage: discover candidates, enrich with full metadata."""

from __future__ import annotations

import logging
from datetime import datetime

from config import Config
from github_client import GitHubClient
from models import RepoCandidate, RepoRecord
from sources.trending import fetch_trending
from sources.search import fetch_search

logger = logging.getLogger(__name__)


def discover_candidates(client: GitHubClient, cfg: Config) -> list[RepoCandidate]:
    """Gather candidates from all sources and deduplicate."""
    candidates: list[RepoCandidate] = []
    candidates.extend(fetch_trending(limit=cfg.trending_limit))
    candidates.extend(fetch_search(client, keywords=cfg.ai_keywords, limit=cfg.search_limit))

    # Deduplicate by full_name (keep first seen)
    seen: set[str] = set()
    unique: list[RepoCandidate] = []
    for c in candidates:
        key = c.full_name.lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    logger.info("Candidates after dedup: %d (from %d)", len(unique), len(candidates))
    return unique


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except ValueError:
        return None


def enrich_candidate(client: GitHubClient, candidate: RepoCandidate) -> RepoRecord:
    """Fetch full repo details, README, latest release."""
    repo = client.get_repo(candidate.full_name)
    readme = client.get_readme(candidate.full_name)
    release = client.get_latest_release(candidate.full_name)

    license_info = repo.get("license") or {}
    topics = repo.get("topics", [])

    record = RepoRecord(
        full_name=repo.get("full_name", candidate.full_name),
        html_url=repo.get("html_url", candidate.html_url),
        description=repo.get("description") or "",
        stars_total=repo.get("stargazers_count", 0),
        forks=repo.get("forks_count", 0),
        watchers=repo.get("subscribers_count", 0),
        open_issues_count=repo.get("open_issues_count", 0),
        language=repo.get("language") or "",
        topics=topics,
        license_spdx=license_info.get("spdx_id") or "",
        default_branch=repo.get("default_branch", "main"),
        pushed_at=_parse_dt(repo.get("pushed_at")),
        updated_at=_parse_dt(repo.get("updated_at")),
        created_at=_parse_dt(repo.get("created_at")),
        readme_text=readme[:8000],  # trim for summarizer
    )

    if release:
        record.release_latest_tag = release.get("tag_name", "")
        record.release_published_at = _parse_dt(release.get("published_at"))

    return record


def collect_all(client: GitHubClient, cfg: Config) -> list[RepoRecord]:
    """Full collect stage: discover + enrich."""
    candidates = discover_candidates(client, cfg)
    records: list[RepoRecord] = []
    for i, c in enumerate(candidates):
        logger.debug("Enriching %d/%d: %s", i + 1, len(candidates), c.full_name)
        try:
            rec = enrich_candidate(client, c)
            records.append(rec)
        except Exception as exc:
            logger.warning("Failed to enrich %s: %s", c.full_name, exc)
    logger.info("Enriched %d / %d candidates", len(records), len(candidates))
    return records
