"""
Custom OpenAPI schema generator for the Quantara API.

Replaces FastAPI's default ``app.openapi()`` with a function that:

* Injects the :class:`~web_app.api.errors.ErrorEnvelope` component schema.
* Adds standardised 400 / 401 / 404 / 422 / 500 response examples to every
  endpoint that does not already declare them.
* Ensures ``/docs`` (Swagger UI) and ``/redoc`` are always available.

Usage (in ``main.py``)::

    from web_app.api.openapi import build_custom_openapi
    app.openapi = build_custom_openapi(app)
"""

from __future__ import annotations

from typing import Callable

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from web_app.api.errors import COMMON_ERROR_RESPONSES, ErrorEnvelope


def build_custom_openapi(app: FastAPI) -> Callable[[], dict]:
    """
    Return a zero-argument callable that produces (and caches) the enriched
    OpenAPI schema for *app*.

    The returned callable is meant to be assigned directly to
    ``app.openapi``::

        app.openapi = build_custom_openapi(app)
    """

    def custom_openapi() -> dict:
        # Use cached schema if already generated (FastAPI's own caching pattern).
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            license_info=app.license_info,
            routes=app.routes,
        )

        # ----------------------------------------------------------------
        # 1. Inject the ErrorEnvelope component schema so that $ref works.
        # ----------------------------------------------------------------
        components = openapi_schema.setdefault("components", {})
        schemas = components.setdefault("schemas", {})

        # Generate the JSON schema from the Pydantic model.
        envelope_schema = ErrorEnvelope.model_json_schema()
        # Remove any $defs nesting – we want a flat component entry.
        envelope_schema.pop("$defs", None)
        schemas["ErrorEnvelope"] = envelope_schema

        # ----------------------------------------------------------------
        # 2. Enrich every path/operation with common error responses.
        # ----------------------------------------------------------------
        for _path, path_item in openapi_schema.get("paths", {}).items():
            for _method, operation in path_item.items():
                if not isinstance(operation, dict):
                    continue  # skip non-operation keys like "parameters"

                responses = operation.setdefault("responses", {})
                for status_code, response_spec in COMMON_ERROR_RESPONSES.items():
                    str_code = str(status_code)
                    # Only add if the endpoint hasn't declared its own.
                    if str_code not in responses:
                        responses[str_code] = response_spec

        # ----------------------------------------------------------------
        # 3. Add top-level API info tags description.
        # ----------------------------------------------------------------
        openapi_schema.setdefault("tags", [])
        _ensure_tag(openapi_schema, "Health", "Service health and readiness probes.")
        _ensure_tag(openapi_schema, "Positions", "Leveraged position lifecycle management.")
        _ensure_tag(openapi_schema, "Dashboard", "Aggregated portfolio metrics.")
        _ensure_tag(openapi_schema, "User", "User profile and contract management.")
        _ensure_tag(openapi_schema, "Vault", "Collateral vault deposits and balances.")
        _ensure_tag(openapi_schema, "Leaderboard", "Protocol-wide leaderboard statistics.")
        _ensure_tag(openapi_schema, "Referral", "Referral link generation and tracking.")
        _ensure_tag(openapi_schema, "Telegram", "Telegram mini-app integration.")
        _ensure_tag(openapi_schema, "Auth", "Wallet-based authentication (Stellar).")
        _ensure_tag(openapi_schema, "Metrics", "Prometheus metrics endpoint.")

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return custom_openapi


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_tag(schema: dict, name: str, description: str) -> None:
    """Add a tag entry to the schema if not already present."""
    existing_names = {t.get("name") for t in schema.get("tags", [])}
    if name not in existing_names:
        schema["tags"].append({"name": name, "description": description})
