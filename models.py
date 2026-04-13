"""Data models used across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RepoCandidate:
    """Minimal info discovered from trending / search."""
    full_name: str          # "owner/repo"
    html_url: str
    source: str             # "trending" | "search"
    discovered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RepoRecord:
    """Full metadata after enrichment."""
    # Identity
    full_name: str
    html_url: str
    description: str = ""

    # Metrics
    stars_total: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues_count: int = 0

    # Metadata
    language: str = ""
    topics: list[str] = field(default_factory=list)
    license_spdx: str = ""
    default_branch: str = "main"

    # Dates
    pushed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Content
    readme_text: str = ""
    release_latest_tag: str = ""
    release_published_at: Optional[datetime] = None

    # Computed (filled by score stage)
    star_growth_7d: int = 0
    recency_days: float = 0.0
    activity_score: float = 0.0
    readme_quality_score: float = 0.0
    trend_score: float = 0.0

    # Classification (filled by classify stage)
    category: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class RepoSummary:
    """Final summary card for output."""
    full_name: str
    html_url: str
    category: str
    tags: list[str] = field(default_factory=list)

    one_liner: str = ""
    highlights: list[str] = field(default_factory=list)   # max 3
    risks: list[str] = field(default_factory=list)         # max 2

    quick_facts: dict = field(default_factory=dict)
    # {stars_total, star_growth_7d, last_update, license}

    recommended_action: str = ""   # Explore | POC | Track | Ignore

    trend_score: float = 0.0


@dataclass
class PushResult:
    """Outcome of a push attempt."""
    success: bool
    status_code: int = 0
    response_text: str = ""
    retries: int = 0
    payload_bytes: int = 0
    error: str = ""


@dataclass
class RunArtifact:
    """Metadata for a single pipeline run."""
    run_id: str                 # YYYYMMDD
    run_at: datetime = field(default_factory=datetime.utcnow)
    candidates_count: int = 0
    filtered_count: int = 0
    selected_count: int = 0
    push_result: Optional[PushResult] = None
