"""
Backend tests for the WalletConnect-style pairing router (Issue #273).

These tests mock the redis client so no external Redis is required.
The rate limiter is disabled by the autouse `disable_rate_limiting`
fixture in conftest.py.
"""

import json
import secrets
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from web_app.api.walletconnect import router

app = FastAPI()
app.include_router(router)


VALID_STELLAR_PUBKEY = "GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
assert len(VALID_STELLAR_PUBKEY) == 56


class _FakeRedis:
    """Tiny in-memory Redis substitute that supports setex / get / delete
    semantics used by the walletconnect router.

    Stores strings under whatever key was provided, plus soft-TTL — when
    setex is called again under the same key the previous value is
    overwritten.
    """

    def __init__(self):
        self.store = {}
        # public_key -> signed_xdr mapping so XDR source-account checks
        # have something realistic to verify against.
        self.xdr_resolver = {}

    async def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        return int(self.store.pop(key, None) is not None)


@pytest.fixture
def fake_redis():
    """Patch the private `_redis_client` inside the walletconnect module
    so every endpoint uses our in-memory fake."""
    fake = _FakeRedis()
    with patch("web_app.api.walletconnect._redis_client", fake):
        yield fake


@pytest.fixture
def patch_strkey_validation(monkeypatch):
    """Stub the StrKey validator so tests don't need the stellar-sdk."""

    def fake_is_valid_ed25519_public_key(_pk):
        return _pk == VALID_STELLAR_PUBKEY

    monkeypatch.setattr(
        "web_app.api.walletconnect._is_valid_stellar_pubkey",
        fake_is_valid_ed25519_public_key,
    )
    monkeypatch.setattr(
        "web_app.api.walletconnect._is_valid_stellar_secret",
        fake_is_valid_ed25519_public_key,
    )
    # XDR source account resolver — return the same pubkey we configured
    # so the source-account check passes.
    monkeypatch.setattr(
        "web_app.api.walletconnect._xdr_source_account",
        lambda _xdr: VALID_STELLAR_PUBKEY,
    )


@pytest.mark.asyncio
async def test_pair_creates_session_with_wc_uri(fake_redis, patch_strkey_validation):
    client = TestClient(app)
    resp = client.post("/api/walletconnect/pair", json={"action": "connect", "network": "TESTNET"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == {"session_id", "topic", "sym_key", "uri", "expires_at"}
    assert body["uri"].startswith("wc:")
    assert body["uri"].__contains__("@2?symKey=")
    assert body["uri"].endswith("&relay-protocol=irn")
    # Redis stores the active session so poll can read it.
    key = f"walletconnect:pair:{body['session_id']}"
    blob = json.loads(await fake_redis.get(key))
    assert blob["state"] == "pending"


@pytest.mark.asyncio
async def test_poll_returns_pending_state(fake_redis, patch_strkey_validation):
    client = TestClient(app)
    pair = client.post("/api/walletconnect/pair", json={"action": "connect"}).json()
    poll = client.get(f"/api/walletconnect/poll/{pair['session_id']}")
    assert poll.status_code == 200
    assert poll.json()["state"] == "pending"


@pytest.mark.asyncio
async def test_poll_returns_404_for_unknown_session(fake_redis, patch_strkey_validation):
    client = TestClient(app)
    resp = client.get("/api/walletconnect/poll/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_complete_approves_when_publickey_valid(fake_redis, patch_strkey_validation):
    client = TestClient(app)
    pair = client.post("/api/walletconnect/pair", json={"action": "connect"}).json()
    resp = client.post(
        f"/api/walletconnect/complete/{pair['session_id']}",
        json={"public_key": VALID_STELLAR_PUBKEY},
    )
    assert resp.status_code == 200, resp.text
    poll = client.get(f"/api/walletconnect/poll/{pair['session_id']}")
    assert poll.json()["public_key"] == VALID_STELLAR_PUBKEY
    assert poll.json()["state"] == "approved"


@pytest.mark.asyncio
async def test_complete_rejects_invalid_pubkey(fake_redis, patch_strkey_validation):
    client = TestClient(app)
    pair = client.post("/api/walletconnect/pair", json={"action": "connect"}).json()
    resp = client.post(
        f"/api/walletconnect/complete/{pair['session_id']}",
        json={"public_key": "not-a-stellar-key"},
    )
    # Pydantic field validator surfaces a 422 to the client.
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_complete_rejects_xdr_with_mismatched_source_account(
    fake_redis, patch_strkey_validation, monkeypatch
):
    """If the mobile wallet uploads an XDR whose source account isn't the
    pubkey it claimed, that means the wallet was trying to sign a
    transaction for a different account and we must refuse."""
    client = TestClient(app)
    pair = client.post("/api/walletconnect/pair", json={"action": "connect"}).json()
    client.post(
        f"/api/walletconnect/complete/{pair['session_id']}",
        json={"public_key": VALID_STELLAR_PUBKEY},
    )

    # Open a signing sub-session.
    sign = client.post(
        "/api/walletconnect/sign",
        json={"session_id": pair["session_id"], "xdr": "AAAA", "network": "TESTNET"},
    )
    assert sign.status_code == 200, sign.text
    sub_sid = sign.json()["sub_session_id"]

    # Override the XDR source-account resolver to return a DIFFERENT pubkey
    # so the mismatch check fires.
    monkeypatch.setattr(
        "web_app.api.walletconnect._xdr_source_account",
        lambda _xdr: "GBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"[:56],
    )

    resp = client.post(
        f"/api/walletconnect/complete/{sub_sid}",
        json={"signed_xdr": "AAAA"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sign_sub_session_then_complete_signed_xdr(
    fake_redis, patch_strkey_validation
):
    client = TestClient(app)
    pair = client.post("/api/walletconnect/pair", json={"action": "connect"}).json()
    # Approve pairing.
    client.post(
        f"/api/walletconnect/complete/{pair['session_id']}",
        json={"public_key": VALID_STELLAR_PUBKEY},
    )

    sign = client.post(
        "/api/walletconnect/sign",
        json={"session_id": pair["session_id"], "xdr": "AAAA", "network": "TESTNET"},
    )
    sub_sid = sign.json()["sub_session_id"]

    resp = client.post(
        f"/api/walletconnect/complete/{sub_sid}",
        json={"signed_xdr": "BASE64SIGNEDXDR"},
    )
    assert resp.status_code == 200

    poll = client.get(f"/api/walletconnect/poll/{sub_sid}")
    assert poll.json()["state"] == "signed"
    assert poll.json()["signed_xdr"] == "BASE64SIGNEDXDR"


@pytest.mark.asyncio
async def test_delete_session_removes_entry(fake_redis, patch_strkey_validation):
    client = TestClient(app)
    pair = client.post("/api/walletconnect/pair", json={"action": "connect"}).json()
    resp = client.delete(f"/api/walletconnect/session/{pair['session_id']}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    # Subsequent poll should 404.
    poll = client.get(f"/api/walletconnect/poll/{pair['session_id']}")
    assert poll.status_code == 404


@pytest.mark.asyncio
async def test_network_field_rejects_unknown_values(
    fake_redis, patch_strkey_validation
):
    client = TestClient(app)
    resp = client.post("/api/walletconnect/pair", json={"network": "WRONG_NET"})
    assert resp.status_code == 422
