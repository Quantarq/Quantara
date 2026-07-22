"""Tests for RequireJsonContentTypeMiddleware (issue #205).

Mounted on a tiny FastAPI app so these tests do not pull the full
application stack (Redis, DB, Sentry, etc.).
"""

import json

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from web_app.api.middleware import (
    DEFAULT_MUTATING_PATH_PREFIXES,
    RequireJsonContentTypeMiddleware,
)


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/api/save-bug-report")
    async def save_bug(request: Request):
        return {"received": True, "is_mutating": getattr(request.state, "is_mutating", None)}

    @app.post("/api/add-extra-deposit/{position_id}")
    async def extra_deposit(position_id: str, request: Request):
        return {
            "position_id": position_id,
            "is_mutating": getattr(request.state, "is_mutating", None),
        }

    @app.post("/api/other")
    async def other():
        return {"other": True}

    app.add_middleware(RequireJsonContentTypeMiddleware)
    return app


@pytest.fixture
def client():
    return TestClient(_build_app())


def test_post_text_plain_rejected_on_bug_report(client):
    response = client.post(
        "/api/save-bug-report",
        content=b"not-json",
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 415
    body = response.json()
    assert "application/json" in body.get("accept", "")
    assert response.headers.get("accept") == "application/json"


def test_post_json_accepted_on_bug_report(client):
    response = client.post(
        "/api/save-bug-report",
        json={"title": "x", "body": "y"},
    )
    assert response.status_code == 200
    assert response.json()["received"] is True


def test_post_json_with_charset_accepted(client):
    response = client.post(
        "/api/save-bug-report",
        content=json.dumps({"title": "x"}).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    assert response.status_code == 200


def test_post_form_urlencoded_rejected_on_extra_deposit(client):
    response = client.post(
        "/api/add-extra-deposit/pos-1",
        data={"amount": "1"},
    )
    assert response.status_code == 415


def test_get_health_never_triggers_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_unlisted_post_not_constrained(client):
    # Paths outside the mutating prefix list stay unrestricted.
    response = client.post(
        "/api/other",
        content=b"anything",
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 200
    assert response.json() == {"other": True}


def test_default_prefixes_cover_issue_targets():
    assert any(p.startswith("/api/add-extra-deposit") for p in DEFAULT_MUTATING_PATH_PREFIXES)
    assert "/api/save-bug-report" in DEFAULT_MUTATING_PATH_PREFIXES
