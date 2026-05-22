"""Formatting templates for ingest output."""

from __future__ import annotations

from typing import Callable

from linglong.ingest.templates.morning_brief import format_morning_brief

TEMPLATES: dict[str, Callable] = {
    "morning-brief": format_morning_brief,
}


def get_template(name: str) -> Callable | None:
    """Get a formatting template by name."""
    return TEMPLATES.get(name)
