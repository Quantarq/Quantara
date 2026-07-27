from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from web_app.api.main import app
from web_app.api.pausable import pause_controller
from web_app.db.database import get_database


ADMIN_HEADERS = {"X-Admin-Token": "test-admin-token"}


def test_admin_can_pause_and_unpause_protocol(monkeypatch):
    monkeypatch.setenv("PAUSE_ADMIN_TOKEN", "test-admin-token")
    pause_controller.unpause()
    app.dependency_overrides[get_database] = lambda: MagicMock()
    client = TestClient(app)

    assert client.get("/api/admin/pause", headers=ADMIN_HEADERS).json() == {
        "paused": False
    }

    pause_response = client.post("/api/admin/pause", headers=ADMIN_HEADERS)
    assert pause_response.status_code == 200
    assert pause_response.json() == {"paused": True}

    blocked_response = client.get("/api/check-user?wallet_id=test-wallet")
    assert blocked_response.status_code == 503
    assert blocked_response.json() == {"detail": "Protocol paused"}

    unpause_response = client.delete("/api/admin/pause", headers=ADMIN_HEADERS)
    assert unpause_response.status_code == 200
    assert unpause_response.json() == {"paused": False}

    app.dependency_overrides.clear()


def test_pause_admin_requires_token(monkeypatch):
    monkeypatch.setenv("PAUSE_ADMIN_TOKEN", "test-admin-token")
    pause_controller.unpause()
    client = TestClient(app)

    response = client.post("/api/admin/pause", headers={"X-Admin-Token": "wrong"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin authorization required"}
