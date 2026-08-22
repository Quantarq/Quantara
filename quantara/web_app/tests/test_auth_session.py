from unittest.mock import patch, AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from web_app.api.auth import router

app = FastAPI()
app.include_router(router)


@pytest.fixture
def client():
    return TestClient(app)


def _patch_store(wallet_id):
    """Return a patch context that replaces session_store.get_wallet_id."""
    mock = AsyncMock(return_value=wallet_id)
    return patch("web_app.api.auth.session_store.get_wallet_id", mock)


class TestGetSessionValidCookie:
    def test_valid_cookie_returns_wallet_id(self, client):
        with _patch_store("STELLAR-123"):
            resp = client.get(
                "/api/auth/session",
                cookies={"wallet_id": "valid-token"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["authenticated"] is True
        assert body["walletId"] == "STELLAR-123"


class TestGetSessionMissingCookie:
    def test_no_cookie_returns_401(self, client):
        resp = client.get("/api/auth/session")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "No active wallet session"


class TestGetSessionExpiredCookie:
    def test_expired_cookie_returns_401(self, client):
        with _patch_store(None):
            resp = client.get(
                "/api/auth/session",
                cookies={"wallet_id": "expired-token"},
            )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "No active wallet session"


class TestGetSessionBackwardCompat:
    def test_query_param_still_works(self, client):
        resp = client.get("/api/auth/session?wallet_id=QRPARAM-456")
        assert resp.status_code == 200
        body = resp.json()
        assert body["authenticated"] is True
        assert body["walletId"] == "QRPARAM-456"

    def test_query_param_takes_precedence_over_cookie(self, client):
        with _patch_store("COOKIE-WALLET") as mock_get:
            resp = client.get(
                "/api/auth/session?wallet_id=QUERY-WALLET",
                cookies={"wallet_id": "cookie-token"},
            )
        assert resp.status_code == 200
        assert resp.json()["walletId"] == "QUERY-WALLET"
        mock_get.assert_not_called()
