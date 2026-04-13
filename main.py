"""AI GitHub Radar – main orchestrator.

Usage:
    python main.py          # Run the full daily pipeline
    python main.py --dry    # Skip Teams push (local artifacts only)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import load_config, Config
from github_client import GitHubClient
from models import RunArtifact
from pipeline.collect import collect_all
from pipeline.filter import filter_records
from pipeline.score import compute_scores
from pipeline.classify import classify_records
from pipeline.summarize import summarize_records
from pipeline.render import render_digest_md, render_summary_page_md, render_summary_page_html
from pipeline.push import build_teams_payload_messagecard, enforce_teams_payload_limits, send_to_teams_workflow
from storage.state import RunState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("radar")


def _select_for_output(records, cfg: Config):
    """Select top-K overall + top-M per category."""
    selected = list(records[:cfg.top_overall])
    seen = {r.full_name for r in selected}

    cats: dict[str, list] = {}
    for r in records:
        cats.setdefault(r.category, []).append(r)

    for cat, items in cats.items():
        count = 0
        for r in items:
            if r.full_name not in seen:
                selected.append(r)
                seen.add(r.full_name)
                count += 1
            if count >= cfg.top_per_category:
                break

    return selected


def run_pipeline(cfg: Config, dry_run: bool = False) -> RunArtifact:
    """Execute the full radar pipeline."""
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d")
    artifact = RunArtifact(run_id=run_id, run_at=now)

    logger.info("═══ AI GitHub Radar – Run %s ═══", run_id)

    # --- Output directory ---
    out_dir = cfg.output_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    site_dir = Path("site")
    site_dir.mkdir(parents=True, exist_ok=True)

    # --- State ---
    state = RunState(cfg.output_dir / "state.json")

    # --- GitHub client ---
    client = GitHubClient(token=cfg.github_token)

    try:
        # B) Discover
        logger.info("── Step 1: Discover candidates ──")
        records = collect_all(client, cfg)
        artifact.candidates_count = len(records)

        # D) Filter
        logger.info("── Step 2: Filter noise ──")
        filtered = filter_records(records, cfg)
        artifact.filtered_count = len(filtered)

        if not filtered:
            logger.warning("No repos passed filters. Aborting.")
            return artifact

        # E) Score & Rank
        logger.info("── Step 3: Score & rank ──")
        scored = compute_scores(filtered)

        # F) Classify
        logger.info("── Step 4: Classify ──")
        classified = classify_records(scored)

        # Select for output
        selected = _select_for_output(classified, cfg)
        artifact.selected_count = len(selected)

        # G) Summarize
        logger.info("── Step 5: Summarize (%d repos) ──", len(selected))
        summaries = summarize_records(
            selected,
            openai_api_key=cfg.openai_api_key,
            openai_model=cfg.openai_model,
        )

        # H) Render
        logger.info("── Step 6: Render outputs ──")
        summary_page_md = render_summary_page_md(summaries, run_id)
        summary_page_html = render_summary_page_html(summaries, run_id)
        digest_md = render_digest_md(summaries, run_id, summary_page_link=cfg.summary_page_url)

        # J) Persist artifacts
        (out_dir / "summary_page.md").write_text(summary_page_md, encoding="utf-8")
        (out_dir / "digest.md").write_text(digest_md, encoding="utf-8")
        (site_dir / "index.html").write_text(summary_page_html, encoding="utf-8")

        # Debug artifact
        debug_data = [
            {"full_name": s.full_name, "category": s.category,
             "trend_score": round(s.trend_score, 4), "stars": s.quick_facts.get("stars_total")}
            for s in summaries
        ]
        (out_dir / "run.json").write_text(
            json.dumps(debug_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        state.update(run_id, [s.full_name for s in summaries])
        logger.info("Artifacts saved to %s", out_dir)

        # I) Push
        if cfg.teams_enable and not dry_run:
            logger.info("── Step 7: Push to Teams ──")
            # Build top-lines for MessageCard
            top_lines = "\n".join(
                f"- **[{s.full_name}]({s.html_url})** – {s.one_liner}"
                for s in summaries[:5]
            )
            cat_block: dict[str, list] = {}
            for s in summaries:
                cat_block.setdefault(s.category, []).append(s)
            cat_md = "\n".join(
                f"**{cat}**: " + ", ".join(f"[{s.full_name}]({s.html_url})" for s in items[:2])
                for cat, items in sorted(cat_block.items())
            )

            payload = build_teams_payload_messagecard(
                run_date=run_id,
                digest_title=f"🚀 Daily AI GitHub Radar – {run_id}",
                top_lines_md=top_lines,
                category_md=cat_md,
                summary_link=cfg.summary_page_url,
            )
            payload = enforce_teams_payload_limits(payload)
            result = send_to_teams_workflow(
                webhook_url=cfg.teams_workflow_webhook_url,
                payload=payload,
                timeout_s=cfg.teams_timeout_seconds,
                max_retries=cfg.teams_max_retries,
            )
            artifact.push_result = result
            if result.success:
                logger.info("✅ Teams push succeeded (HTTP %d, %d bytes, %d retries)",
                            result.status_code, result.payload_bytes, result.retries)
            else:
                logger.error("❌ Teams push failed: %s", result.error)
        else:
            logger.info("Teams push skipped (dry_run=%s, teams_enable=%s)", dry_run, cfg.teams_enable)

    finally:
        client.close()

    logger.info("═══ Run %s complete ═══", run_id)
    return artifact


def main():
    parser = argparse.ArgumentParser(description="AI GitHub Radar – daily pipeline")
    parser.add_argument("--dry", action="store_true", help="Skip Teams push")
    args = parser.parse_args()

    cfg = load_config()

    if not cfg.github_token:
        logger.error("GITHUB_TOKEN is required. Set it in .env or environment.")
        sys.exit(1)

    artifact = run_pipeline(cfg, dry_run=args.dry)
    logger.info(
        "Summary: candidates=%d, filtered=%d, selected=%d",
        artifact.candidates_count, artifact.filtered_count, artifact.selected_count,
    )


if __name__ == "__main__":
    main()
