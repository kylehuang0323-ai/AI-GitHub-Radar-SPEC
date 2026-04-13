"""Classify pipeline stage: assign categories and tags to repositories."""

from __future__ import annotations

import logging
import re

from models import RepoRecord

logger = logging.getLogger(__name__)

# Keyword -> category mapping (checked in order; first match wins)
_CATEGORY_RULES: list[tuple[list[str], str]] = [
    (["rag", "retrieval", "vector", "embedding", "chroma", "pinecone", "weaviate", "faiss"],
     "RAG & Retrieval"),
    (["serving", "inference", "quant", "quantiz", "vllm", "onnx", "triton", "trt", "tensorrt", "deploy"],
     "Inference & Deployment"),
    (["agent", "tool-use", "planner", "langchain", "llamaindex", "autogen", "crewai", "swarm"],
     "LLM / Agent"),
    (["eval", "benchmark", "tracing", "observability", "guardrail", "safety", "monitor"],
     "Evaluation & Observability"),
    (["finetune", "fine-tune", "lora", "qlora", "trainer", "deepspeed", "peft", "train"],
     "Training & Fine-tuning"),
    (["multimodal", "vision", "audio", "speech", "image", "video", "diffusion"],
     "Multimodal"),
    (["label", "annotation", "dataset", "data-", "synthetic"],
     "Data & Labeling"),
    (["security", "compliance", "audit", "rbac", "encrypt"],
     "Security & Compliance"),
]

_RUNTIME_KEYWORDS = {
    "cli": ["cli", "command-line", "terminal"],
    "sdk": ["sdk", "library", "pip install", "npm install"],
    "webui": ["webui", "web ui", "gradio", "streamlit", "dashboard"],
    "api": ["api", "rest", "grpc", "openapi", "fastapi", "flask"],
}

_MATURITY_SIGNALS = {
    "production-ready": ["production", "stable", "v1.", "1.0"],
    "beta": ["beta", "v0.", "0.9", "pre-release"],
    "poc": ["experimental", "poc", "proof of concept", "alpha", "wip"],
}


def _searchable(record: RepoRecord) -> str:
    return " ".join([
        record.full_name.lower(),
        record.description.lower(),
        " ".join(record.topics),
        record.readme_text[:3000].lower(),
    ])


def _classify_category(text: str) -> str:
    for keywords, category in _CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return "AI Applications"


def _infer_tags(record: RepoRecord, text: str) -> list[str]:
    tags: list[str] = []

    # Language tag
    if record.language:
        tags.append(record.language)

    # Runtime tags
    for tag, kws in _RUNTIME_KEYWORDS.items():
        if any(kw in text for kw in kws):
            tags.append(tag)

    # Maturity
    combined = text + " " + record.release_latest_tag.lower()
    for maturity, kws in _MATURITY_SIGNALS.items():
        if any(kw in combined for kw in kws):
            tags.append(maturity)
            break

    # License
    if record.license_spdx:
        tags.append(record.license_spdx)

    return tags


def classify_records(records: list[RepoRecord]) -> list[RepoRecord]:
    """Assign category and tags to each record."""
    for rec in records:
        text = _searchable(rec)
        rec.category = _classify_category(text)
        rec.tags = _infer_tags(rec, text)

    cats = {}
    for rec in records:
        cats[rec.category] = cats.get(rec.category, 0) + 1
    logger.info("Classification distribution: %s", cats)
    return records
