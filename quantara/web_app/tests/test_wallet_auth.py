"""
Tests for wallet signature authentication (Issue #41, #192).

Covers:
- Nonce generation: uniqueness, storage, binding to wallet_id.
- Nonce consumption: valid path, replay prevention, wrong wallet, unknown nonce.
- Signature verification: valid key, wrong key, tampered message, bad hex, bad public key.
- verify_wallet_signature dependency: 401 on bad nonce, 401 on bad sig, wallet_id on success.
- GET /api/auth/nonce endpoint: returns nonce + expires_in.
"""

import pytest
import fakeredis.aioredis
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch

from web_app.api.wallet_auth import (
    NONCE_TTL,
    NONCE_KEY_PREFIX,
    _consume_nonce,
    _generate_nonce,
    _nonce_key,
    _verify_stellar_signature,
    router,
    verify_wallet_signature,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
async def _mock_redis():
    """Mock Redis with fakeredis for all tests."""
    fake_redis = fakeredis.aioredis.FakeRedis()
    with patch("web_app.api.wallet_auth._redis") as mock_redis:
        mock_redis.return_value = fake_redis
        # Clear all nonce keys before and after each test
        async def clear_keys():
            keys = await fake_redis.keys(f"{NONCE_KEY_PREFIX}*")
            if keys:
                await fake_redis.delete(*keys)
        await clear_keys()
        yield fake_redis
        await clear_keys()


# ---------------------------------------------------------------------------
# Nonce generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGenerateNonce:
    async def test_returns_64_char_hex_string(self):
        nonce = await _generate_nonce("GABCDEF")
        assert isinstance(nonce, str)
        assert len(nonce) == 64

    async def test_each_call_produces_unique_nonce(self):
        n1 = await _generate_nonce("GABCDEF")
        n2 = await _generate_nonce("GABCDEF")
        assert n1 != n2

    async def test_nonce_stored_with_correct_wallet_id(self, _mock_redis):
        wallet_id = "GABCDEF123"
        nonce = await _generate_nonce(wallet_id)
        stored_wallet = await _mock_redis.get(_nonce_key(nonce))
        assert stored_wallet == wallet_id


# ---------------------------------------------------------------------------
# Nonce consumption
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestConsumeNonce:
    async def test_valid_nonce_and_wallet_returns_true(self):
        wallet_id = "GABCDEF"
        nonce = await _generate_nonce(wallet_id)
        assert await _consume_nonce(nonce, wallet_id) is True

    async def test_nonce_removed_after_consumption(self, _mock_redis):
        wallet_id = "GABCDEF"
        nonce = await _generate_nonce(wallet_id)
        await _consume_nonce(nonce, wallet_id)
        stored_wallet = await _mock_redis.get(_nonce_key(nonce))
        assert stored_wallet is None

    async def test_replay_attack_fails(self):
        wallet_id = "GABCDEF"
        nonce = await _generate_nonce(wallet_id)
        assert await _consume_nonce(nonce, wallet_id) is True
        assert await _consume_nonce(nonce, wallet_id) is False

    async def test_wrong_wallet_id_returns_false(self):
        nonce = await _generate_nonce("GOWNER")
        assert await _consume_nonce(nonce, "GATTACKER") is False

    async def test_unknown_nonce_returns_false(self):
        assert await _consume_nonce("deadbeef" * 8, "GABCDEF") is False


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

class TestVerifyStellarSignature:
    def test_valid_signature_returns_true(self):
        from stellar_sdk import Keypair
        kp = Keypair.random()
        message = "test_nonce_abcdef0123456789"
        sig_hex = kp.sign(message.encode()).hex()
        assert _verify_stellar_signature(kp.public_key, message, sig_hex) is True

    def test_wrong_keypair_returns_false(self):
        from stellar_sdk import Keypair
        signer = Keypair.random()
        verifier = Keypair.random()
        message = "some_nonce"
        sig_hex = signer.sign(message.encode()).hex()
        assert _verify_stellar_signature(verifier.public_key, message, sig_hex) is False

    def test_tampered_message_returns_false(self):
        from stellar_sdk import Keypair
        kp = Keypair.random()
        message = "original_nonce"
        sig_hex = kp.sign(message.encode()).hex()
        assert _verify_stellar_signature(kp.public_key, "tampered_nonce", sig_hex) is False

    def test_non_hex_signature_returns_false(self):
        from stellar_sdk import Keypair
        kp = Keypair.random()
        assert _verify_stellar_signature(kp.public_key, "nonce", "not_hex!!") is False

    def test_malformed_public_key_returns_false(self):
        assert _verify_stellar_signature("INVALID_KEY", "nonce", "ab" * 32) is False


# ---------------------------------------------------------------------------
# verify_wallet_signature FastAPI dependency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dependency_raises_401_on_invalid_nonce():
    with pytest.raises(HTTPException) as exc_info:
        await verify_wallet_signature(
            x_wallet_id="GABCDEF",
            x_nonce="does_not_exist_at_all",
            x_signature="ab" * 32,
        )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_dependency_raises_401_on_bad_signature():
    from stellar_sdk import Keypair
    kp = Keypair.random()
    nonce = await _generate_nonce(kp.public_key)
    with pytest.raises(HTTPException) as exc_info:
        await verify_wallet_signature(
            x_wallet_id=kp.public_key,
            x_nonce=nonce,
            x_signature="aa" * 32,  # wrong signature
        )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_dependency_returns_wallet_id_on_valid_signature():
    from stellar_sdk import Keypair
    kp = Keypair.random()
    nonce = await _generate_nonce(kp.public_key)
    sig_hex = kp.sign(nonce.encode()).hex()
    result = await verify_wallet_signature(
        x_wallet_id=kp.public_key,
        x_nonce=nonce,
        x_signature=sig_hex,
    )
    assert result == kp.public_key


# ---------------------------------------------------------------------------
# GET /api/auth/nonce endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_nonce_endpoint_returns_nonce_and_ttl(_mock_redis):
    mini_app = FastAPI()
    mini_app.include_router(router)
    test_client = TestClient(mini_app)

    wallet_id = "GABCDEF123TEST"
    response = test_client.get("/api/auth/nonce", params={"wallet_id": wallet_id})

    assert response.status_code == 200
    data = response.json()
    assert "nonce" in data
    assert "expires_in" in data
    assert data["expires_in"] == NONCE_TTL
    assert len(data["nonce"]) == 64


def test_get_nonce_endpoint_missing_wallet_id_returns_422():
    mini_app = FastAPI()
    mini_app.include_router(router)
    test_client = TestClient(mini_app)

    response = test_client.get("/api/auth/nonce")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_nonce_endpoint_stores_nonce_bound_to_wallet(_mock_redis):
    mini_app = FastAPI()
    mini_app.include_router(router)
    test_client = TestClient(mini_app)

    wallet_id = "GBOUND_TEST_WALLET"
    response = test_client.get("/api/auth/nonce", params={"wallet_id": wallet_id})
    nonce = response.json()["nonce"]

    stored_wallet = await _mock_redis.get(_nonce_key(nonce))
    assert stored_wallet == wallet_id
