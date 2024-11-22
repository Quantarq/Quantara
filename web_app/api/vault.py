"""
Module for handling vault deposit operations in the SPOTNET API.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from web_app.db.crud import DepositDBConnector
from web_app.db.models import User
from web_app.schemas.vault import VaultDepositRequest, VaultDepositResponse
from web_app.db.crud import UserDBConnector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vault", tags=["vault"])

@router.post("/deposit", response_model=VaultDepositResponse)
async def deposit_to_vault(
    request: VaultDepositRequest,
    db: DepositDBConnector = Depends(DepositDBConnector)
) -> VaultDepositResponse:
    try:
        logger.info(f"Processing deposit request for wallet {request.wallet_id}")
        
       
        user_db = UserDBConnector()
        user = user_db.get_user_by_wallet_id(request.wallet_id)
        if not user:
            user = user_db.create_user(request.wallet_id)
            
        vault = db.create_vault(
            user=user,
            symbol=request.symbol,
            amount=request.amount
        )
        
        return VaultDepositResponse(
            deposit_id=vault.id,
            wallet_id=request.wallet_id,
            amount=request.amount,
            symbol=request.symbol,
            status="pending"
        )
    except Exception as e:
        logger.error(f"Error processing deposit: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process deposit: {str(e)}"
        )
