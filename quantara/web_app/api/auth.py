from fastapi import APIRouter, Response, HTTPException, Request, status, Header, Depends
from pydantic import BaseModel

from web_app.api.rate_limiter import limiter, WRITE_LIMIT, USER_DATA_LIMIT
from web_app.api.wallet_auth import verify_wallet_signature
from web_app.api.session import session_store
import logging

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

class WalletAuthRequest(BaseModel):
    wallet_id: str
    signature: str

@router.post("/connect")
@limiter.limit(WRITE_LIMIT)
async def connect_wallet(
    request: Request, 
    payload: WalletAuthRequest, 
    response: Response,
    x_nonce: str = Header(..., description="Nonce obtained from GET /api/auth/nonce")
):
    # Verify the stellar signature
    wallet_id = await verify_wallet_signature(
        x_wallet_id=payload.wallet_id,
        x_nonce=x_nonce,
        x_signature=payload.signature
    )
    
    # Create session token
    session_token = await session_store.create_session(wallet_id)

    # Set the httpOnly cookie securely
    response.set_cookie(
        key="wallet_id",
        value=session_token,
        httponly=True,            # Prevents JavaScript reading (XSS proof)
        secure=True,              # Requires HTTPS
        samesite="strict",        # Mitigates CSRF attacks
        max_age=60 * 60 * 24 * 7, # 1 week session lifecycle
        path="/",
    )
    
    return {"success": True, "walletId": wallet_id}

@router.get("/session")
@limiter.limit(USER_DATA_LIMIT)
async def get_session(request: Request, wallet_id: str | None = None):
    """
    Endpoint for frontend initialization to verify if a valid httpOnly 
    cookie session exists without exposing the raw cookie to client JS.
    """
    # Note: Your REPO-002 auth middleware will automatically populate wallet_id from the cookie
    if not wallet_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="No active wallet session"
        )
    return {"authenticated": True, "walletId": wallet_id}

@router.post("/logout")
@limiter.limit(USER_DATA_LIMIT)
async def logout_wallet(request: Request, response: Response):
    # Invalidate session in Redis
    session_token = request.cookies.get("wallet_id")
    if session_token:
        await session_store.delete_session(session_token)

    # Explicitly flush the cookie out of the client browser
    response.delete_cookie(
        key="wallet_id",
        path="/",
        secure=True,
        httponly=True,
        samesite="strict"
    )
    return {"success": True}