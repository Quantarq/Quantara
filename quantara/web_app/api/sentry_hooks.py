"""Sentry hooks that enforce safe operator-facing event payloads."""

from typing import Any

from web_app.utils.scrub import scrub_user_text_for_sentry

BUG_REPORT_CONTEXT = "bug_report"
DESCRIPTION_FIELD = "description"


def _scrub_description(mapping: Any) -> None:
    if isinstance(mapping, dict) and DESCRIPTION_FIELD in mapping:
        mapping[DESCRIPTION_FIELD] = scrub_user_text_for_sentry(
            mapping[DESCRIPTION_FIELD]
        )


def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """Scrub bug report text before Sentry persists an event."""
    contexts = event.get("contexts")
    if isinstance(contexts, dict):
        _scrub_description(contexts.get(BUG_REPORT_CONTEXT))

    _scrub_description(event.get("extra"))
    return event