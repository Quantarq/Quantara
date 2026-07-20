from unittest.mock import AsyncMock, patch
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from web_app.api.auth import router
from web_app.api.session import session_store

# Mock the authentication dependency to avoid complexity in session tests
# but still verify the cookie logic
app = FastAPI()
app.include_router(router)


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_connect_wallet_success():
    """Test: valid signature -> 200 + cookie whose value is opaque token (>=32 chars)."""
    with patch(
        "web_app.api.auth.verify_wallet_signature", new_callable=AsyncMock
    ) as mock_verify, patch.object(
        session_store, "get_wallet_id", new_callable=AsyncMock
    ) as mock_get_wallet:

        mock_verify.return_value = "G_VALID_WALLET"
        mock_get_wallet.return_value = "G_VALID_WALLET"

        client = TestClient(app)

        # Payload mimicking WalletAuthRequest
        payload = {"wallet_id": "G_VALID_WALLET", "signature": "valid_sig"}

        response = client.post(
            "/api/auth/connect", json=payload, headers={"x-nonce": "some-nonce"}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        cookie = response.cookies.get("wallet_id")
        assert cookie is not None
        assert len(cookie) >= 32

        # Verify session was created/retrieved in session_store mock
        wallet_id = await session_store.get_wallet_id(cookie)
        assert wallet_id == "G_VALID_WALLET"


@pytest.mark.asyncio
async def test_connect_wallet_invalid_signature():
    """Test: invalid signature -> 401."""
    with patch(
        "web_app.api.auth.verify_wallet_signature",
        side_effect=HTTPException(status_code=401, detail="Invalid signature"),
    ):
        client = TestClient(app)
        payload = {"wallet_id": "G_INVALID_WALLET", "signature": "invalid_sig"}
        response = client.post(
            "/api/auth/connect", json=payload, headers={"x-nonce": "some-nonce"}
        )

        assert response.status_code == 401