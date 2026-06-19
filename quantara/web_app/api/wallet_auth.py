"""Wallet authentication: Ed25519 challenge-response signature verification."""
import secrets
import time
from typing import Dict, Tuple

from fastapi import APIRouter, Header, HTTPException, Query

from stellar_sdk import Keypair

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

_nonce_store: Dict[str, Tuple[str, float]] = {}
NONCE_TTL: int = 300  # seconds


def _clean_expired_nonces() -> None:
    """Remove nonces past their TTL."""
    cutoff = time.monotonic() - NONCE_TTL
    expired = [n for n, (_, ts) in _nonce_store.items() if ts < cutoff]
    for n in expired:
        _nonce_store.pop(n, None)


def _generate_nonce(wallet_id: str) -> str:
    """Generate a cryptographically secure nonce bound to wallet_id."""
    _clean_expired_nonces()
    nonce = secrets.token_hex(32)
    _nonce_store[nonce] = (wallet_id, time.monotonic())
    return nonce


def _consume_nonce(nonce: str, wallet_id: str) -> bool:
    """
    Validate and consume a nonce atomically.
    Returns True only when the nonce exists, has not expired, and belongs to wallet_id.
    The nonce is always removed to prevent replay even on a wallet mismatch.
    """
    _clean_expired_nonces()
    entry = _nonce_store.pop(nonce, None)
    if entry is None:
        return False
    stored_wallet_id, _ = entry
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
    nonce = _generate_nonce(wallet_id)
    return {"nonce": nonce, "expires_in": NONCE_TTL}


async def verify_wallet_signature(
    x_wallet_id: str = Header(..., description="Stellar public key of the signer"),
    x_nonce: str = Header(..., description="Nonce obtained from GET /api/auth/nonce"),
    x_signature: str = Header(..., description="Hex-encoded Ed25519 signature of the nonce"),
) -> str:
    """FastAPI dependency -- verifies a Stellar wallet signature and returns the wallet_id."""
    if not _consume_nonce(x_nonce, x_wallet_id):
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
