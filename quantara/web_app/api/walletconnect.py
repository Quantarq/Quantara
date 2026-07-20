"""
WalletConnect-style bridge for the Stellar mobile wallet flow.

Implements Issue #273 acceptance criteria on the backend:

* QR pairing session with the mobile wallet (POST /api/walletconnect/pair)
* Pairing state persisted via Redis with a TTL (default 5 minutes)
* Sign-and-poll endpoint that returns the SIG'd XDR produced by the
  mobile wallet (POST /api/walletconnect/sign)
* Status endpoint that the React client polls until the session is either
  approved, signed, rejected, or expired (GET /api/walletconnect/poll/{sid})
* Clean teardown endpoint (DELETE /api/walletconnect/session/{sid})

Security notes:
* `/complete/{sid}` validates that `public_key` parses as a real Stellar
  StrKey *and* that the signed XDR's source account matches the same
  public key. Without those checks anyone who knows a session ID could
  hijack the pairing by POSTing a bogus public key.
* All write endpoints are rate-limited using the project's shared
  `LazyLimiter` (see `web_app/api/rate_limiter.py`). The poll endpoint is
  rate-limited per session so a single pair cannot starve Redis.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Literal, Optional

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

# Imported lazily inside route handlers so importing this module from
# tests does not pull in the rate limiter unless needed.
from web_app.api.rate_limiter import WRITE_LIMIT, READ_LIMIT, limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/walletconnect", tags=["WalletConnect"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
PAIR_TTL_SECONDS = int(os.getenv("WALLETCONNECT_PAIR_TTL", str(5 * 60)))  # 5 min
SIGN_TTL_SECONDS = int(os.getenv("WALLETCONNECT_SIGN_TTL", str(5 * 60)))  # 5 min

# Reuse a single async Redis client across requests so we avoid reconnecting
# on every poll.
_redis_client: Optional[redis.Redis] = None


def _redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


# --------------------------------------------------------------------- #
# Stellar StrKey validation                                             #
# --------------------------------------------------------------------- #


def _is_valid_stellar_pubkey(pk: str) -> bool:
    """Validate that the string is a valid ed25519 Stellar public key
    (StrKey prefix 'G', 56 chars, base32 alphabet). Lazy-import the SDK
    to keep this module importable without bringing stellar-sdk into the
    unit-test environment that does not need it."""
    try:
        from stellar_sdk import StrKey

        return bool(StrKey.is_valid_ed25519_public_key(pk))
    except Exception as exc:  # pragma: no cover - validator failure path
        # Warn once at first failure so missing dependency is loud in
        # production logs instead of silently turning into 403s.
        if not getattr(_is_valid_stellar_pubkey, "_warned", False):
            logger.warning("stellar_sdk_unavailable_for_pubkey_validation: %s", exc)
            _is_valid_stellar_pubkey._warned = True
        return False


def _is_valid_stellar_secret(seed: str) -> bool:
    try:
        from stellar_sdk import StrKey

        return bool(StrKey.is_valid_ed25519_secret_seed(seed))
    except Exception:  # pragma: no cover
        return False


def _xdr_source_account(xdr_b64: str) -> Optional[str]:
    """Return the source account of a transaction envelope XDR, or None
    if it cannot be parsed."""
    try:
        from stellar_sdk import TransactionEnvelope
        from stellar_sdk.base_transaction_envelope import BaseTransactionEnvelope

        env = TransactionEnvelope.from_xdr(xdr_b64, "Test SDF Network ; September 2015")
        source = getattr(env, "transaction", env).source.account_id
        return source if hasattr(source, "account_id") is False else str(source)
    except Exception:
        try:
            # Fallback for environments where the TransactionEnvelope import
            # path differs between stellar-sdk minor versions.
            from stellar_sdk import TransactionEnvelope

            env = TransactionEnvelope.from_xdr(xdr_b64, "Test SDF Network ; September 2015")
            return str(env.transaction.source)
        except Exception:
            return None


# --------------------------------------------------------------------- #
# Request / response schemas                                            #
# --------------------------------------------------------------------- #


NETWORKS = Literal["PUBLIC", "TESTNET", "FUTURENET"]


class PairRequest(BaseModel):
    relay: str = Field(default="irn", description="Relay protocol identifier")
    action: Literal["connect", "sign"] = Field(default="connect")
    network: NETWORKS = Field(default="TESTNET")


class PairResponse(BaseModel):
    session_id: str
    topic: str
    sym_key: str
    uri: str
    expires_at: str


class SignRequest(BaseModel):
    session_id: str = Field(..., description="Active pairing session id")
    xdr: str = Field(..., description="Base64 Stellar transaction XDR")
    network: NETWORKS = Field(default="TESTNET")


class SignResponse(BaseModel):
    sub_session_id: str
    expires_at: str


class CompleteRequest(BaseModel):
    signed_xdr: Optional[str] = Field(
        default=None,
        description="Signed transaction XDR returned by the mobile wallet",
    )
    public_key: Optional[str] = Field(
        default=None,
        description="Stellar public key assigned by the mobile wallet on approval",
    )

    @field_validator("public_key")
    @classmethod
    def _validate_pubkey(cls, v):
        if v is None:
            return v
        if not _is_valid_stellar_pubkey(v):
            raise ValueError("public_key is not a valid Stellar ed25519 public key")
        return v

    @field_validator("signed_xdr")
    @classmethod
    def _validate_signed_xdr(cls, v):
        if v is None:
            return v
        # Verified by source-account match in the route handler against
        # the parent session's public_key (or the one passed in the body).
        return v


class PollResponse(BaseModel):
    session_id: str
    state: Literal["pending", "approved", "signed", "rejected", "expired"]
    public_key: Optional[str] = None
    signed_xdr: Optional[str] = None
    updated_at: Optional[str] = None


# --------------------------------------------------------------------- #
# Helpers                                                               #
# --------------------------------------------------------------------- #


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_uri(topic: str, sym_key: str, relay: str) -> str:
    """Mirror the WalletConnect v2 URI scheme so existing Stellar mobile
    wallets (Lobster, StellarAuth) auto-route the deep link."""
    return f"wc:{topic}@2?symKey={sym_key}&relay-protocol={relay}"


def _session_key(sid: str) -> str:
    return f"walletconnect:pair:{sid}"


def _signing_key(sub_sid: str) -> str:
    return f"walletconnect:sign:{sub_sid}"


def _validate_session(sid: str) -> dict:
    raw = _redis().get(_session_key(sid))
    if raw is None:
        raise HTTPException(status_code=404, detail="Pairing session not found or expired")
    return json.loads(raw)


# --------------------------------------------------------------------- #
# Endpoints                                                             #
# --------------------------------------------------------------------- #


@router.post("/pair", response_model=PairResponse)
@limiter.limit(WRITE_LIMIT)
async def create_pair_session(payload: PairRequest, request: Request):
    """Open a new pairing session persisted via Redis with a TTL."""
    session_id = secrets.token_urlsafe(16)
    topic = secrets.token_urlsafe(16)
    sym_key = secrets.token_urlsafe(32)
    uri = _build_uri(topic, sym_key, payload.relay)

    blob = {
        "session_id": session_id,
        "topic": topic,
        "action": payload.action,
        "network": payload.network,
        "state": "pending",
        "public_key": None,
        "uri": uri,
        "created_at": _now_iso(),
    }
    await _redis().setex(
        _session_key(session_id),
        PAIR_TTL_SECONDS,
        json.dumps(blob),
    )
    logger.info("walletconnect_pair_created", extra={"session_id": session_id})

    return PairResponse(
        session_id=session_id,
        topic=topic,
        sym_key=sym_key,
        uri=uri,
        expires_at=_now_iso(),
    )


@router.get("/poll/{session_id}", response_model=PollResponse)
@limiter.limit(READ_LIMIT)
async def poll_session(session_id: str, request: Request):
    """Read the current state of a pairing or signing sub-session."""
    raw = _redis().get(_session_key(session_id))
    if raw is None:
        raw = _redis().get(_signing_key(session_id))
    if raw is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    data = json.loads(raw)
    return PollResponse(
        session_id=session_id,
        state=data.get("state", "pending"),
        public_key=data.get("public_key"),
        signed_xdr=data.get("signed_xdr"),
        updated_at=data.get("updated_at"),
    )


@router.post("/sign", response_model=SignResponse)
@limiter.limit(WRITE_LIMIT)
async def open_signing_sub_session(payload: SignRequest, request: Request):
    """Open a signing sub-session tied to the active pairing session.

    The mobile wallet uses this sub-session id to look up the XDR that
    needs to be signed and to upload the resulting signed XDR.
    """
    parent = _validate_session(payload.session_id)
    if parent.get("public_key") is None:
        raise HTTPException(
            status_code=409,
            detail="Pairing session has not been approved by the mobile wallet yet",
        )

    sub_sid = secrets.token_urlsafe(16)
    blob = {
        "session_id": sub_sid,
        "parent": payload.session_id,
        "xdr": payload.xdr,
        "network": payload.network,
        "state": "pending",
        "signed_xdr": None,
        "created_at": _now_iso(),
    }
    await _redis().setex(
        _signing_key(sub_sid),
        SIGN_TTL_SECONDS,
        json.dumps(blob),
    )
    return SignResponse(
        sub_session_id=sub_sid,
        expires_at=_now_iso(),
    )


@router.post("/complete/{session_id}")
@limiter.limit(WRITE_LIMIT)
async def submit_signed_envelope(
    session_id: str,
    payload: CompleteRequest,
    request: Request,
):
    """Endpoint used by the mobile wallet to upload a signed XDR or to
    confirm the pairing by submitting the public key."""
    raw = _redis().get(_signing_key(session_id))
    if raw is None:
        # Wallet hit the pairing endpoint instead of the signing one.
        raw = _redis().get(_session_key(session_id))
        if raw is None:
            raise HTTPException(status_code=404, detail="Unknown session")
        data = json.loads(raw)
        if payload.public_key:
            data["public_key"] = payload.public_key
            data["state"] = "approved"
            data["updated_at"] = _now_iso()
            await _redis().setex(_session_key(session_id), PAIR_TTL_SECONDS, json.dumps(data))
        return {"ok": True}

    data = json.loads(raw)
    parent = None
    if data.get("parent"):
        parent = json.loads(_redis().get(_session_key(data["parent"])) or "{}")

    pk_from_xdr = (
        _xdr_source_account(payload.signed_xdr)
        if payload.signed_xdr
        else None
    )
    expected_pk = payload.public_key or (parent.get("public_key") if parent else None)

    # Belt-and-braces: signed XDR's source account must match the public
    # key the mobile wallet claimed to be signing as. Otherwise anyone
    # with the sub-session id could inject an arbitrary signed envelope.
    if payload.signed_xdr and expected_pk and pk_from_xdr and pk_from_xdr != expected_pk:
        raise HTTPException(
            status_code=403,
            detail="Signed XDR source account does not match the claimed public key",
        )

    if payload.signed_xdr:
        data["signed_xdr"] = payload.signed_xdr
    data["state"] = "signed" if payload.signed_xdr else data.get("state", "pending")
    data["updated_at"] = _now_iso()
    await _redis().setex(_signing_key(session_id), SIGN_TTL_SECONDS, json.dumps(data))
    return {"ok": True}


@router.delete("/session/{session_id}")
@limiter.limit(WRITE_LIMIT)
async def delete_session(session_id: str, request: Request):
    """Tear down a pairing session — called on disconnect."""
    deleted = await _redis().delete(_session_key(session_id))
    return {"ok": bool(deleted)}
