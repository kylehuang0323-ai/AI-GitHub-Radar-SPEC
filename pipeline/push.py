"""Push pipeline stage: send daily digest to Teams via Workflows webhook."""

from __future__ import annotations

import json
import logging
import random
import time

import httpx

from models import PushResult

logger = logging.getLogger(__name__)

_PAYLOAD_MAX_BYTES = 28 * 1024  # 28 KB Teams limit


# ─────────── Payload construction ───────────

def build_teams_payload_messagecard(
    run_date: str,
    digest_title: str,
    top_lines_md: str,
    category_md: str,
    summary_link: str,
) -> dict:
    """Return a MessageCard JSON payload (simple + link-only)."""
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": f"Daily AI GitHub Radar – {run_date}",
        "themeColor": "0076D7",
        "title": digest_title,
        "text": top_lines_md,
        "sections": [
            {
                "activityTitle": "🔥 Top Trending",
                "text": top_lines_md,
            },
            {
                "activityTitle": "🧠 By Category",
                "text": category_md,
            },
        ],
    }

    if summary_link:
        payload["sections"].append({
            "activityTitle": "👉 Full Report",
            "text": f"[Open summary page]({summary_link})",
        })

    return payload


# ─────────── Payload trimming ───────────

def enforce_teams_payload_limits(payload: dict, max_bytes: int = _PAYLOAD_MAX_BYTES) -> dict:
    """
    Ensure payload <= 28KB. Trimming priority:
    1) Remove category section text
    2) Trim top lines to 3 items
    3) Truncate text fields
    4) Final fallback: title + link only
    """
    def _size() -> int:
        return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    if _size() <= max_bytes:
        return payload

    # Step 1: simplify category section
    for sec in payload.get("sections", []):
        if sec.get("activityTitle", "").startswith("🧠"):
            sec["text"] = "See full report for category breakdown."
    if _size() <= max_bytes:
        return payload

    # Step 2: shorten top-lines text
    text = payload.get("text", "")
    lines = text.strip().splitlines()
    if len(lines) > 3:
        payload["text"] = "\n".join(lines[:3]) + "\n..."
        for sec in payload.get("sections", []):
            if sec.get("activityTitle", "").startswith("🔥"):
                sec["text"] = payload["text"]
    if _size() <= max_bytes:
        return payload

    # Step 3: truncate all text fields
    for sec in payload.get("sections", []):
        if len(sec.get("text", "")) > 200:
            sec["text"] = sec["text"][:200] + "…"
    if _size() <= max_bytes:
        return payload

    # Step 4: nuclear option – title + link only
    summary_link = ""
    for sec in payload.get("sections", []):
        if "summary page" in sec.get("text", "").lower():
            summary_link = sec["text"]
            break
    payload["text"] = summary_link or "Daily digest available."
    payload["sections"] = []

    return payload


# ─────────── Send with retry ───────────

def send_to_teams_workflow(
    webhook_url: str,
    payload: dict,
    timeout_s: int = 10,
    max_retries: int = 5,
) -> PushResult:
    """POST JSON to Teams Workflows webhook with exponential backoff."""
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    payload_bytes = len(raw)
    logger.info("Teams payload size: %d bytes (limit %d)", payload_bytes, _PAYLOAD_MAX_BYTES)

    retries = 0
    backoff_base = 1.0

    for attempt in range(1, max_retries + 1):
        try:
            resp = httpx.post(
                webhook_url,
                content=raw,
                headers={"Content-Type": "application/json"},
                timeout=timeout_s,
            )
        except httpx.HTTPError as exc:
            logger.warning("Teams POST failed (attempt %d): %s", attempt, exc)
            if attempt == max_retries:
                return PushResult(
                    success=False, retries=retries,
                    payload_bytes=payload_bytes, error=str(exc),
                )
            retries += 1
            time.sleep(backoff_base * (2 ** (attempt - 1)))
            continue

        logger.info("Teams response: HTTP %d", resp.status_code)

        if 200 <= resp.status_code < 300:
            return PushResult(
                success=True, status_code=resp.status_code,
                response_text=resp.text[:200], retries=retries,
                payload_bytes=payload_bytes,
            )

        if resp.status_code in (429, 500, 502, 503, 504):
            sleep = backoff_base * (2 ** (attempt - 1))
            jitter = random.uniform(0, 0.25 * sleep)
            total_sleep = sleep + jitter
            logger.warning("HTTP %d – retry %d/%d in %.1fs", resp.status_code, attempt, max_retries, total_sleep)
            retries += 1
            time.sleep(total_sleep)
            continue

        # Non-retryable error
        return PushResult(
            success=False, status_code=resp.status_code,
            response_text=resp.text[:200], retries=retries,
            payload_bytes=payload_bytes,
            error=f"HTTP {resp.status_code}",
        )

    return PushResult(
        success=False, retries=retries,
        payload_bytes=payload_bytes, error="Max retries exceeded",
    )
