"""Discover candidates from GitHub Trending page (HTML scraping)."""

from __future__ import annotations

import logging
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from models import RepoCandidate

logger = logging.getLogger(__name__)

TRENDING_URL = "https://github.com/trending"


def fetch_trending(language: str = "", since: str = "daily", limit: int = 50) -> list[RepoCandidate]:
    """Scrape GitHub Trending and return RepoCandidate list."""
    params: dict[str, str] = {"since": since}
    if language:
        params["spoken_language_code"] = language

    try:
        resp = httpx.get(TRENDING_URL, params=params, timeout=20, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch trending: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    candidates: list[RepoCandidate] = []

    for article in soup.select("article.Box-row")[:limit]:
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        href = h2.get("href", "").strip("/")
        if "/" not in href:
            continue
        candidates.append(RepoCandidate(
            full_name=href,
            html_url=f"https://github.com/{href}",
            source="trending",
            discovered_at=datetime.utcnow(),
        ))

    logger.info("Trending: discovered %d candidates", len(candidates))
    return candidates
