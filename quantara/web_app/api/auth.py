from fastapi import APIRouter, Response, HTTPException, Request, status
from pydantic import BaseModel

from web_app.api.rate_limiter import limiter, WRITE_LIMIT, USER_DATA_LIMIT

router = APIRouter(prefix="/api/auth", tags=["auth"])

class WalletAuthRequest(BaseModel):
    wallet_id: str
    signature: str  # Assuming signature validation happens here

@router.post("/connect")
@limiter.limit(WRITE_LIMIT)
async def connect_wallet(request: Request, payload: WalletAuthRequest, response: Response):
    # 1. Perform signature verification checks here...
    # (Validated via your REPO-002 auth middleware)
    
    wallet_id = payload.wallet_id

    # 2. Set the httpOnly cookie securely
    response.set_cookie(
        key="wallet_id",
        value=wallet_id,
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
    # Explicitly flush the cookie out of the client browser
    response.delete_cookie(
        key="wallet_id",
        path="/",
        secure=True,
        httponly=True,
        samesite="strict"
    )
    return {"success": True}