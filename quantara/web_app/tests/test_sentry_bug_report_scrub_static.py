"""Static checks for Sentry bug-report sanitization wiring."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_API = (ROOT / "api" / "user.py").read_text()
MAIN_API = (ROOT / "api" / "main.py").read_text()
SCRUB = (ROOT / "utils" / "scrub.py").read_text()
HOOKS = (ROOT / "api" / "sentry_hooks.py").read_text()


def test_bug_report_endpoint_sends_only_scrubbed_description_to_sentry():
    assert "safe_description = scrub_user_text_for_sentry(report.bug_description)" in USER_API
    assert 'extras={"description": safe_description}' in USER_API
    assert '"description": report.bug_description' not in USER_API
    assert 'extras={"description": report.bug_description}' not in USER_API


def test_sentry_before_send_hook_is_registered():
    assert "from web_app.api.sentry_hooks import before_send" in MAIN_API
    assert "before_send=before_send" in MAIN_API


def test_scrubber_escapes_html_and_enforces_cap_with_marker():
    assert "html.escape(text, quote=True)" in SCRUB
    assert "MAX_SENTRY_TEXT_LENGTH = 1000" in SCRUB
    assert 'TRUNCATION_MARKER = "...[truncated]"' in SCRUB
    assert "text[: max_length - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER" in SCRUB


def test_before_send_enforces_scrub_on_context_and_extra_payloads():
    assert 'BUG_REPORT_CONTEXT = "bug_report"' in HOOKS
    assert 'DESCRIPTION_FIELD = "description"' in HOOKS
    assert 'contexts.get(BUG_REPORT_CONTEXT)' in HOOKS
    assert 'event.get("extra")' in HOOKS
    assert "scrub_user_text_for_sentry(" in HOOKS