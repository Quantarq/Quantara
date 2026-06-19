"""
Tests for wallet signature authentication (Issue #41).

Covers:
- Nonce generation: uniqueness, storage, binding to wallet_id.
- Nonce consumption: valid path, replay prevention, wrong wallet, unknown nonce.
- Nonce expiry: expired nonces are pruned by _clean_expired_nonces.
- Signature verification: valid key, wrong key, tampered message, bad hex, bad public key.
- verify_wallet_signature dependency: 401 on bad nonce, 401 on bad sig, wallet_id on success.
- GET /api/auth/nonce endpoint: returns nonce + expires_in.
"""

import time

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from web_app.api.wallet_auth import (
    NONCE_TTL,
    _clean_expired_nonces,
    _consume_nonce,
    _generate_nonce,
    _nonce_store,
    _verify_stellar_signature,
    router,
    verify_wallet_signature,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_nonce_store():
    """Ensure an empty nonce store before and after every test."""
    _nonce_store.clear()
    yield
    _nonce_store.clear()


# ---------------------------------------------------------------------------
# Nonce generation
# ---------------------------------------------------------------------------

class TestGenerateNonce:
    def test_returns_64_char_hex_string(self):
        nonce = _generate_nonce("GABCDEF")
        assert isinstance(nonce, str)
        assert len(nonce) == 64

    def test_each_call_produces_unique_nonce(self):
        n1 = _generate_nonce("GABCDEF")
        n2 = _generate_nonce("GABCDEF")
        assert n1 != n2

    def test_nonce_stored_with_correct_wallet_id(self):
        wallet_id = "GABCDEF123"
        nonce = _generate_nonce(wallet_id)
        assert nonce in _nonce_store
        stored_wallet, _ = _nonce_store[nonce]
        assert stored_wallet == wallet_id

    def test_nonce_stored_with_recent_timestamp(self):
        before = time.monotonic()
        nonce = _generate_nonce("GTEST")
        after = time.monotonic()
        _, ts = _nonce_store[nonce]
        assert before <= ts <= after


# ---------------------------------------------------------------------------
# Nonce consumption
# ---------------------------------------------------------------------------

class TestConsumeNonce:
    def test_valid_nonce_and_wallet_returns_true(self):
        wallet_id = "GABCDEF"
        nonce = _generate_nonce(wallet_id)
        assert _consume_nonce(nonce, wallet_id) is True

    def test_nonce_removed_after_consumption(self):
        wallet_id = "GABCDEF"
        nonce = _generate_nonce(wallet_id)
        _consume_nonce(nonce, wallet_id)
        assert nonce not in _nonce_store

    def test_replay_attack_fails(self):
        wallet_id = "GABCDEF"
        nonce = _generate_nonce(wallet_id)
        assert _consume_nonce(nonce, wallet_id) is True
        assert _consume_nonce(nonce, wallet_id) is False

    def test_wrong_wallet_id_returns_false(self):
        nonce = _generate_nonce("GOWNER")
        assert _consume_nonce(nonce, "GATTACKER") is False

    def test_unknown_nonce_returns_false(self):
        assert _consume_nonce("deadbeef" * 8, "GABCDEF") is False


# ---------------------------------------------------------------------------
# Nonce expiry
# ---------------------------------------------------------------------------

class TestCleanExpiredNonces:
    def test_removes_expired_nonce(self):
        wallet_id = "GEXPIRED"
        nonce = _generate_nonce(wallet_id)
        _nonce_store[nonce] = (wallet_id, time.monotonic() - NONCE_TTL - 1)
        _clean_expired_nonces()
        assert nonce not in _nonce_store

    def test_retains_fresh_nonce(self):
        wallet_id = "GFRESH"
        nonce = _generate_nonce(wallet_id)
        _clean_expired_nonces()
        assert nonce in _nonce_store

    def test_generate_nonce_prunes_expired_entries(self):
        wallet_id = "GSTALE"
        stale_nonce = _generate_nonce(wallet_id)
        _nonce_store[stale_nonce] = (wallet_id, time.monotonic() - NONCE_TTL - 1)
        _generate_nonce("GNEW")
        assert stale_nonce not in _nonce_store


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
    nonce = _generate_nonce(kp.public_key)
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
    nonce = _generate_nonce(kp.public_key)
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

def test_get_nonce_endpoint_returns_nonce_and_ttl():
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


def test_get_nonce_endpoint_stores_nonce_bound_to_wallet():
    mini_app = FastAPI()
    mini_app.include_router(router)
    test_client = TestClient(mini_app)

    wallet_id = "GBOUND_TEST_WALLET"
    response = test_client.get("/api/auth/nonce", params={"wallet_id": wallet_id})
    nonce = response.json()["nonce"]

    assert nonce in _nonce_store
    stored_wallet, _ = _nonce_store[nonce]
    assert stored_wallet == wallet_id
