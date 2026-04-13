"""Pipeline utility helpers."""

from __future__ import annotations


def truncate(text: str, max_len: int = 200, suffix: str = "…") -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix
