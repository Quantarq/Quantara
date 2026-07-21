"""
quantara/web_app/utils/test_sentry_alerts.py

Covers issue #299's acceptance criteria:
  1. A 1% error burst on /api/check-user routes to #oncall-protocol
     (not #oncall-fyi) at critical severity.
  2. Read-route errors demote to info level (route to #oncall-fyi).
  3. Bonus/guard: probe routes never alert, no matter the error rate.

Run with: pytest test_sentry_alerts.py -v
"""

from slo_router import evaluate


def test_auth_mutation_burst_pages_oncall_protocol():
    decision = evaluate(
        route="/api/check-user",
        short_window_error_rate=0.01,   # 1% error burst
        long_window_error_rate=0.01,    # sustained across the 6h window
    )
    assert decision.should_alert is True
    assert decision.route_class == "auth_mutation"
    assert decision.severity == "critical"
    assert decision.channel == "#oncall-protocol"
    assert decision.channel != "#oncall-fyi"


def test_read_route_errors_demote_to_info():
    decision = evaluate(
        route="/api/save-bug-report",
        short_window_error_rate=0.01,   # same 1% burst, but on a read route
        long_window_error_rate=0.01,
    )
    assert decision.should_alert is True
    assert decision.route_class == "read"
    assert decision.severity == "info"
    assert decision.channel == "#oncall-fyi"


def test_read_route_small_blip_does_not_page():
    # 0.1% error rate is well inside the 5% read budget -- should stay silent.
    decision = evaluate(
        route="/api/get-user-profile",
        short_window_error_rate=0.001,
        long_window_error_rate=0.001,
    )
    assert decision.should_alert is False


def test_probe_routes_never_alert():
    for route in ("/health", "/metrics"):
        decision = evaluate(
            route=route,
            short_window_error_rate=1.0,  # even 100% failure
            long_window_error_rate=1.0,
        )
        assert decision.should_alert is False


def test_single_blip_without_sustained_window_does_not_page():
    # Short window spikes but long window hasn't caught up yet --
    # multi-window confirmation should suppress the page.
    decision = evaluate(
        route="/api/check-user",
        short_window_error_rate=0.01,
        long_window_error_rate=0.001,
    )
    assert decision.should_alert is False
