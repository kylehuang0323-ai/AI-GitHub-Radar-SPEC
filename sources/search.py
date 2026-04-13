"""Discover candidates via GitHub Search API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from github_client import GitHubClient
from models import RepoCandidate

logger = logging.getLogger(__name__)


def fetch_search(
    client: GitHubClient,
    keywords: list[str] | None = None,
    created_after_days: int = 7,
    limit: int = 100,
) -> list[RepoCandidate]:
    """Search GitHub for recently-created AI repos with high stars."""
    if keywords is None:
        keywords = ["ai", "llm", "rag", "agent", "inference"]

    since_date = (datetime.utcnow() - timedelta(days=created_after_days)).strftime("%Y-%m-%d")
    topic_query = " OR ".join(f"topic:{kw}" for kw in keywords[:8])
    query = f"({topic_query}) created:>={since_date} stars:>=10"

    candidates: list[RepoCandidate] = []
    per_page = min(limit, 100)
    pages_needed = (limit + per_page - 1) // per_page

    for page in range(1, pages_needed + 1):
        items = client.search_repos(query, sort="stars", per_page=per_page, page=page)
        if not items:
            break
        for item in items:
            candidates.append(RepoCandidate(
                full_name=item["full_name"],
                html_url=item["html_url"],
                source="search",
                discovered_at=datetime.utcnow(),
            ))
        if len(candidates) >= limit:
            break

    candidates = candidates[:limit]
    logger.info("Search: discovered %d candidates", len(candidates))
    return candidates
