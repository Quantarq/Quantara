"""
quantara/web_app/utils/slo_router.py

Small, dependency-light module that:
  1. Loads sentry_alerts.yaml
  2. Classifies a route into a class (probe / auth_mutation / read)
  3. Given an observed error rate over the short and long windows,
     decides whether to fire, and at what severity/channel.

This is intentionally framework-agnostic (no Sentry SDK import) so it
can be unit-tested in isolation, and then called from wherever your
Sentry webhook/cron/synthetic-monitor lives to decide routing.

NOTE: adjust the import path below to match wherever this repo keeps
its utils package.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

CONFIG_PATH = Path(__file__).with_name("sentry_alerts.yaml")


@dataclass
class RouteDecision:
    route: str
    route_class: str
    should_alert: bool
    severity: Optional[str] = None
    channel: Optional[str] = None
    notify: Optional[str] = None


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def classify_route(route: str, config: dict) -> str:
    """Return the class name for a route, first match wins."""
    for class_name, spec in config["route_classes"].items():
        for pattern in spec.get("match", []):
            if fnmatch.fnmatch(route, pattern):
                return class_name
    # Nothing matched at all (shouldn't happen given the "/api/*" catch-all
    # in `read`) -- fail safe to read/info rather than silently paging.
    return "read"


def evaluate(
    route: str,
    short_window_error_rate: float,
    long_window_error_rate: float,
    config: Optional[dict] = None,
) -> RouteDecision:
    """
    error rates are fractions, e.g. 0.01 for a 1% error burst.
    """
    config = config or load_config()
    route_class = classify_route(route, config)
    spec = config["route_classes"][route_class]

    if spec.get("alert", {}).get("disabled"):
        return RouteDecision(route, route_class, should_alert=False)

    thresholds = spec["slo"]["burn_rate_thresholds"]
    fires = (
        short_window_error_rate >= thresholds["short_window_burn_rate"] / 100
        and long_window_error_rate >= thresholds["long_window_burn_rate"] / 100
    )

    if not fires:
        return RouteDecision(route, route_class, should_alert=False)

    alert = spec["alert"]
    return RouteDecision(
        route=route,
        route_class=route_class,
        should_alert=True,
        severity=alert["severity"],
        channel=alert["channel"],
        notify=alert.get("notify"),
    )
