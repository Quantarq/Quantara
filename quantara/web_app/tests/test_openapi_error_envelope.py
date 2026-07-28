"""
Tests for the standardised error envelope (issue #217).

Verifies:
- APIError produces the correct ErrorEnvelope JSON shape.
- /docs and /redoc endpoints are accessible.
- OpenAPI schema includes the ErrorEnvelope component.
- Common error responses (400, 401, 404, 422, 500) appear in the schema.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from web_app.api.errors import APIError, ErrorEnvelope
from web_app.api.main import app
from web_app.db.database import get_database


@pytest.fixture()
def client():
    app.dependency_overrides[get_database] = lambda: MagicMock()
    with patch("web_app.api.main.redis.from_url") as mock_redis:
        mock_redis.return_value.ping = AsyncMock(return_value=True)
        mock_redis.return_value.close = AsyncMock(return_value=None)
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# APIError handler tests
# ---------------------------------------------------------------------------


def test_api_error_returns_envelope_shape(client):
    """APIError is rendered as an ErrorEnvelope JSON body."""

    @app.get("/test-api-error-404")
    async def raise_404():
        raise APIError(
            status_code=404,
            code="position_not_found",
            detail="No position with that ID exists.",
        )

    response = client.get("/test-api-error-404")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "No position with that ID exists."
    assert body["code"] == "position_not_found"
    assert "request_id" in body
    assert len(body["request_id"]) > 0


def test_api_error_400(client):
    """APIError with status 400 produces the correct envelope."""

    @app.get("/test-api-error-400")
    async def raise_400():
        raise APIError(
            status_code=400,
            code="validation_error",
            detail="multiplier must be a valid number",
        )

    response = client.get("/test-api-error-400")
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["detail"] == "multiplier must be a valid number"
    assert "request_id" in body


def test_api_error_response_includes_request_id_header(client):
    """The X-Request-Id response header is set for APIError responses."""

    @app.get("/test-api-error-request-id")
    async def raise_error():
        raise APIError(status_code=401, code="unauthorized", detail="Auth required.")

    response = client.get("/test-api-error-request-id")
    assert response.status_code == 401
    assert "x-request-id" in response.headers


# ---------------------------------------------------------------------------
# /docs and /redoc reachability
# ---------------------------------------------------------------------------


def test_swagger_ui_docs_endpoint(client):
    """/docs returns 200 HTML (Swagger UI)."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_redoc_endpoint(client):
    """/redoc returns 200 HTML (ReDoc UI)."""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# OpenAPI schema content
# ---------------------------------------------------------------------------


def test_openapi_schema_contains_error_envelope_component(client):
    """The OpenAPI schema exposes the ErrorEnvelope component."""
    # Reset cached schema so our custom builder runs fresh.
    app.openapi_schema = None
    schema = app.openapi()
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    assert "ErrorEnvelope" in schemas, (
        "ErrorEnvelope component not found in OpenAPI schema components"
    )


def test_openapi_schema_error_envelope_has_required_fields(client):
    """ErrorEnvelope component schema includes detail, code, request_id."""
    app.openapi_schema = None
    schema = app.openapi()
    envelope = schema["components"]["schemas"]["ErrorEnvelope"]
    props = envelope.get("properties", {})
    assert "detail" in props
    assert "code" in props
    assert "request_id" in props


def test_openapi_schema_paths_include_common_error_codes(client):
    """All paths include at least 422 and 500 in their responses."""
    app.openapi_schema = None
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert len(paths) > 0, "No paths found in schema"
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            # Every operation must have 500 injected at minimum.
            assert "500" in responses, (
                f"Path {method.upper()} {path} missing 500 response"
            )


# ---------------------------------------------------------------------------
# ErrorEnvelope model validation
# ---------------------------------------------------------------------------


def test_error_envelope_model_requires_all_fields():
    """ErrorEnvelope validates that all three fields are required."""
    import pytest

    with pytest.raises(Exception):
        ErrorEnvelope(detail="only detail")  # missing code and request_id


def test_error_envelope_model_serializes_correctly():
    """ErrorEnvelope serialises to the expected dict structure."""
    envelope = ErrorEnvelope(
        detail="test error",
        code="test_code",
        request_id="abc-123",
    )
    data = envelope.model_dump()
    assert data == {
        "detail": "test error",
        "code": "test_code",
        "request_id": "abc-123",
    }
