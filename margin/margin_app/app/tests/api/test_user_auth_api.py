"""
Tests for user auth API endpoints.
"""

import uuid
import pytest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from fastapi import status

from app.main import app
from app.crud.user import user_crud
from app.services.auth.security import verify_password
from app.services.auth.base import create_access_token, create_refresh_token

app.state.settings = SimpleNamespace(
    access_token_expire_minutes=30,
    refresh_token_expire_days=7,
)

client = TestClient(app)

LOGIN_URL = "/api/auth/login"

test_user = SimpleNamespace(
    id=str(uuid.uuid4()),
    email="alice@example.com",
    password="hashed_secret",
    name="Alice",
)

@pytest.fixture(autouse=True)
def patch_get_user():
    """
    patch user_crud.get_object_by_field(...) so it returns our test_user.
    """
    with patch.object(user_crud, "get_object_by_field", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = test_user
        yield mock_get

@pytest.fixture(autouse=True)
def patch_verify_pwd():
    """
    patch verify_password() to return true
    """
    with patch("app.api.auth.verify_password", return_value=True) as mock_verify:
        # mock_verify.return_value = True
        yield mock_verify

@pytest.fixture(autouse=True)
def patch_tokens():
    """
    Patch create_access_token, create_refresh_token to return fixed strings,
    - easy to assert on the response JSON and cookie
    """
    with patch(
        "app.api.auth.create_access_token",
        return_value="fixed-access-token") as mock_access:
        with patch(
            "app.api.auth.create_refresh_token",
            return_value="fixed-refresh-token") as mock_refresh:
            yield (mock_access, mock_refresh)

def test_login_success_sets_cookie_and_returns_access_token(
    patch_get_user, patch_verify_pwd, patch_tokens):
    """ Test successful user login"""
    payload = {"email": test_user.email, "password": "correct-password"}

    response = client.post(LOGIN_URL, json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "access_token": "fixed-access-token",
        "token_type": "bearer",
    }

    cookies = response.cookies
    assert "refresh_token" in cookies
    assert cookies.get("refresh_token") == "fixed-refresh-token"

    patch_get_user.assert_awaited_once_with("email", test_user.email)

    patch_verify_pwd.assert_called_once_with("correct-password", test_user.password)

    create_access_mock, create_refresh_mock = patch_tokens
    create_access_mock.assert_called_once_with(
        test_user.email,
        expires_delta=timedelta(minutes=app.state.settings.access_token_expire_minutes),
    )
    create_refresh_mock.assert_called_once_with(
        test_user.email,
        expires_delta=timedelta(minutes=app.state.settings.refresh_token_expire_days),
    )

def test_login_user_not_found_returns_404(patch_get_user):
    """ Test user when user not found"""
    patch_get_user.return_value = None
    payload = {"email": "no_user@test.com", "password": "whatever"}

    response = client.post(LOGIN_URL, json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "User with this email not found."}
    patch_get_user.assert_awaited_once_with("email", "no_user@test.com")

def test_login_invalid_password_returns_401(patch_verify_pwd):
    """ Test user login with invalid password"""
    patch_verify_pwd.return_value = False
    payload = {"email": test_user.email, "password": "wrong-password"}

    response = client.post(LOGIN_URL, json=payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid credentials"}
    patch_verify_pwd.assert_called_once_with("wrong-password", test_user.password)
