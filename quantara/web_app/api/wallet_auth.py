"""Wallet authentication: Ed25519 challenge-response signature verification.

Nonces are stored in Redis (shared across uvicorn workers and surviving a
deploy) rather than in per-process memory.  Redis TTL handles expiry, so no
manual pruning is required.  The nonce itself is never logged -- it is a seed
for replay attacks if leaked.
"""
import secrets

import redis.asyncio as redis
from fastapi import APIRouter, Header, HTTPException, Query

from stellar_sdk import Keypair

from web_app.contract_tools.cache import get_redis_pool

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

NONCE_TTL: int = 300  # seconds
NONCE_KEY_PREFIX: str = "quantara:nonce:"


async def _redis() -> redis.Redis:
    """Return an async Redis client backed by the shared connection pool."""
    return redis.Redis(connection_pool=await get_redis_pool())


def _nonce_key(nonce: str) -> str:
    return f"{NONCE_KEY_PREFIX}{nonce}"


async def _generate_nonce(wallet_id: str) -> str:
    """Generate a cryptographically secure nonce bound to wallet_id.

    Issued with SET ... EX NONCE_TTL NX so no two workers can ever return the
    same nonce; on the astronomically-unlikely collision we retry.
    """
    client = await _redis()
    while True:
        nonce = secrets.token_hex(32)
        if await client.set(_nonce_key(nonce), wallet_id, ex=NONCE_TTL, nx=True):
            return nonce


async def _consume_nonce(nonce: str, wallet_id: str) -> bool:
    """
    Validate and consume a nonce atomically.
    Returns True only when the nonce exists, has not expired, and belongs to wallet_id.

    GETDEL reads and deletes in a single atomic step, so two concurrent
    consumers of the same nonce get exactly one value and one miss -- and the
    nonce is always removed to prevent replay even on a wallet mismatch.
    """
    client = await _redis()
    stored_wallet_id = await client.getdel(_nonce_key(nonce))
    if stored_wallet_id is None:
        return False
    return stored_wallet_id == wallet_id


def _verify_stellar_signature(public_key: str, message: str, signature_hex: str) -> bool:
    """Verify an Ed25519 signature produced by a Stellar keypair."""
    try:
        keypair = Keypair.from_public_key(public_key)
        sig_bytes = bytes.fromhex(signature_hex)
        keypair.verify(message.encode(), sig_bytes)
        return True
    except Exception:
        return False


@router.get("/nonce", summary="Request a one-time authentication nonce")
async def get_nonce(
    wallet_id: str = Query(..., description="Stellar public key (G...) of the authenticating wallet"),
) -> dict:
    """Issue a one-time nonce for wallet_id.  Sign the nonce with your Stellar private key
    and pass it as X-Signature on the next authenticated request."""
    nonce = await _generate_nonce(wallet_id)
    return {"nonce": nonce, "expires_in": NONCE_TTL}


async def verify_wallet_signature(
    x_wallet_id: str = Header(..., description="Stellar public key of the signer"),
    x_nonce: str = Header(..., description="Nonce obtained from GET /api/auth/nonce"),
    x_signature: str = Header(..., description="Hex-encoded Ed25519 signature of the nonce"),
) -> str:
    """FastAPI dependency -- verifies a Stellar wallet signature and returns the wallet_id."""
    if not await _consume_nonce(x_nonce, x_wallet_id):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired nonce. Request a fresh nonce from /api/auth/nonce.",
        )
    if not _verify_stellar_signature(x_wallet_id, x_nonce, x_signature):
        raise HTTPException(
            status_code=401,
            detail="Signature verification failed. Ensure the nonce was signed with the correct key.",
        )
    return x_wallet_id
