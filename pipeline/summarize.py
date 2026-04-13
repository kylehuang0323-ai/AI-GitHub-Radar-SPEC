"""Summarize pipeline stage: generate concise summary cards for each repo."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime

from models import RepoRecord, RepoSummary

logger = logging.getLogger(__name__)


# ---------- Heuristic summarizer (fallback / no-LLM mode) ----------

def _extract_first_paragraph(readme: str) -> str:
    """Extract first meaningful paragraph from README."""
    lines = readme.strip().splitlines()
    paragraph: list[str] = []
    started = False
    for line in lines:
        stripped = line.strip()
        # Skip badges, titles, blank lines at the top
        if not started:
            if stripped.startswith("#") or stripped.startswith("!") or stripped.startswith("[") or not stripped:
                continue
            started = True
        if started:
            if not stripped:
                if paragraph:
                    break
                continue
            paragraph.append(stripped)
    return " ".join(paragraph)[:200]


def _heuristic_highlights(readme: str) -> list[str]:
    """Extract up to 3 highlight bullet points from README."""
    highlights: list[str] = []
    for m in re.finditer(r"^[-*]\s+\*\*(.+?)\*\*", readme, re.MULTILINE):
        text = m.group(1).strip().rstrip("*")
        if len(text) > 10:
            highlights.append(text)
        if len(highlights) >= 3:
            break
    if not highlights:
        for m in re.finditer(r"^[-*]\s+(.{15,80})$", readme, re.MULTILINE):
            highlights.append(m.group(1).strip())
            if len(highlights) >= 3:
                break
    return highlights


def _heuristic_risks(record: RepoRecord) -> list[str]:
    risks: list[str] = []
    if record.license_spdx in ("NOASSERTION", ""):
        risks.append("License unclear")
    if record.stars_total < 100:
        risks.append("Low star count – early stage")
    if record.release_latest_tag == "":
        risks.append("No formal release yet")
    return risks[:2]


def _recommended_action(record: RepoRecord) -> str:
    if record.trend_score <= 0.05:
        return "Ignore"
    if record.stars_total >= 1000 and record.release_latest_tag:
        return "POC"
    if record.trend_score >= 0.3:
        return "Explore"
    return "Track"


def _summarize_heuristic(record: RepoRecord) -> RepoSummary:
    one_liner = record.description[:120] or _extract_first_paragraph(record.readme_text)
    highlights = _heuristic_highlights(record.readme_text)
    if not highlights and record.description:
        highlights = [record.description[:100]]
    risks = _heuristic_risks(record)

    last_update = ""
    if record.pushed_at:
        last_update = record.pushed_at.strftime("%Y-%m-%d")

    return RepoSummary(
        full_name=record.full_name,
        html_url=record.html_url,
        category=record.category,
        tags=record.tags,
        one_liner=one_liner,
        highlights=highlights,
        risks=risks,
        quick_facts={
            "stars_total": record.stars_total,
            "star_growth_7d": record.star_growth_7d,
            "last_update": last_update,
            "license": record.license_spdx,
        },
        recommended_action=_recommended_action(record),
        trend_score=record.trend_score,
    )


# ---------- LLM summarizer (optional) ----------

def _summarize_llm(record: RepoRecord, model: str, api_key: str) -> RepoSummary:
    """Use OpenAI API to generate a summary card."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed, falling back to heuristic")
        return _summarize_heuristic(record)

    client = OpenAI(api_key=api_key)
    prompt = f"""Summarize this GitHub AI project for a technical audience.

Repository: {record.full_name}
Description: {record.description}
Language: {record.language}
Stars: {record.stars_total}
Topics: {', '.join(record.topics)}

README (excerpt):
{record.readme_text[:3000]}

Respond in this exact JSON format:
{{
  "one_liner": "...(max 25 words)",
  "highlights": ["...", "...", "..."],
  "risks": ["...", "..."],
  "recommended_action": "Explore|POC|Track|Ignore"
}}"""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        import json
        data = json.loads(resp.choices[0].message.content)

        last_update = record.pushed_at.strftime("%Y-%m-%d") if record.pushed_at else ""

        return RepoSummary(
            full_name=record.full_name,
            html_url=record.html_url,
            category=record.category,
            tags=record.tags,
            one_liner=data.get("one_liner", "")[:150],
            highlights=data.get("highlights", [])[:3],
            risks=data.get("risks", [])[:2],
            quick_facts={
                "stars_total": record.stars_total,
                "star_growth_7d": record.star_growth_7d,
                "last_update": last_update,
                "license": record.license_spdx,
            },
            recommended_action=data.get("recommended_action", "Track"),
            trend_score=record.trend_score,
        )
    except Exception as exc:
        logger.warning("LLM summarization failed for %s: %s – falling back", record.full_name, exc)
        return _summarize_heuristic(record)


# ---------- Public API ----------

def summarize_records(
    records: list[RepoRecord],
    openai_api_key: str = "",
    openai_model: str = "gpt-4o-mini",
) -> list[RepoSummary]:
    """Generate summary cards for all provided records."""
    use_llm = bool(openai_api_key)
    summaries: list[RepoSummary] = []
    for rec in records:
        if use_llm:
            s = _summarize_llm(rec, openai_model, openai_api_key)
        else:
            s = _summarize_heuristic(rec)
        summaries.append(s)
    logger.info("Summarized %d repos (mode=%s)", len(summaries), "llm" if use_llm else "heuristic")
    return summaries
