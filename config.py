"""Centralized configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool(val: str | None, default: bool = True) -> bool:
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Config:
    # --- Required ---
    github_token: str = ""
    teams_workflow_webhook_url: str = ""

    # --- Optional: LLM ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- Optional: Output ---
    output_dir: Path = field(default_factory=lambda: Path("./out"))
    top_overall: int = 10
    top_per_category: int = 2

    # --- Optional: Teams ---
    teams_enable: bool = True
    teams_timeout_seconds: int = 10
    teams_max_retries: int = 5

    # --- Optional: Pages ---
    summary_page_url: str = ""

    # --- Discovery ---
    trending_limit: int = 50
    search_limit: int = 100
    ai_keywords: list[str] = field(default_factory=lambda: [
        "ai", "llm", "rag", "agent", "inference", "fine-tune", "finetune",
        "transformer", "diffusion", "multimodal", "embedding", "vector",
        "langchain", "llamaindex", "openai", "ollama", "vllm", "huggingface",
    ])

    # --- Filtering ---
    license_allowlist: list[str] = field(default_factory=lambda: [
        "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
        "MPL-2.0", "ISC", "Unlicense", "0BSD",
    ])
    max_inactive_days: int = 90
    min_readme_length: int = 800


def load_config() -> Config:
    """Build a Config from environment variables."""
    return Config(
        github_token=os.getenv("GITHUB_TOKEN", ""),
        teams_workflow_webhook_url=os.getenv("TEAMS_WORKFLOW_WEBHOOK_URL", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        output_dir=Path(os.getenv("OUTPUT_DIR", "./out")),
        top_overall=int(os.getenv("TOP_OVERALL", "10")),
        top_per_category=int(os.getenv("TOP_PER_CATEGORY", "2")),
        teams_enable=_bool(os.getenv("TEAMS_ENABLE"), default=True),
        teams_timeout_seconds=int(os.getenv("TEAMS_TIMEOUT_SECONDS", "10")),
        teams_max_retries=int(os.getenv("TEAMS_MAX_RETRIES", "5")),
        summary_page_url=os.getenv("SUMMARY_PAGE_URL", ""),
    )
