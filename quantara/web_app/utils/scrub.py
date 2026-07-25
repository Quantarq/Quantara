"""Helpers for removing unsafe user-controlled text from operator telemetry."""

import html
from typing import Any

MAX_SENTRY_TEXT_LENGTH = 1000
TRUNCATION_MARKER = "...[truncated]"


def scrub_user_text_for_sentry(
    value: Any,
    max_length: int = MAX_SENTRY_TEXT_LENGTH,
) -> str:
    """Return bounded, HTML-escaped text safe to render in Sentry UI fields."""
    text = "" if value is None else str(value)
    if max_length < len(TRUNCATION_MARKER):
        raise ValueError("max_length must fit the truncation marker")

    if len(text) > max_length:
        text = text[: max_length - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER

    return html.escape(text, quote=True)