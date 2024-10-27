"""
Handles Telegram webhook integration for the web application.

Provides FastAPI endpoints for setting up webhooks and processing updates
using aiogram and a database connector.
"""

from typing import Literal

from aiogram.types import Update
from aiogram.utils.web_app import check_webapp_signature
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from web_app.api.serializers.telegram import TelegramUserAuth, TelegramUserCreate
from web_app.db.crud import DBConnector, TelegramUserDBConnector
from web_app.telegram import TELEGRAM_TOKEN, bot, dp
from web_app.telegram.utils import build_response_writer, check_telegram_authorization

# Create a FastAPI router for handling Telegram webhook requests
router = APIRouter()
db_connector = DBConnector()
telegram_user_db_connector = TelegramUserDBConnector()


@router.get(
    "/api/webhook/telegram",
    tags=["Telegram Operations"],
    summary="Setup telegram webhook",
)
async def set_telegram_webhook(request: Request) -> Literal["ok"]:
    """
    Set the webhook for the Telegram bot.

    This endpoint sets the webhook URL for the Telegram bot based on the request URL.

    Args:
        request (Request): The FastAPI request object.

    Returns:
        Literal["ok"]: A confirmation message indicating the webhook has been set.
    """
    url = str(request.url.replace(query=""))
    await bot.set_webhook(url=url)
    return "ok"


@router.post("/api/webhook/telegram", include_in_schema=False)
async def telegram_webhook(update: Update):
    """
    Handle incoming updates from Telegram.

    This endpoint processes updates sent to the webhook by Telegram.

    Args:
        update (Update): The update object received from Telegram.

    Returns:
        StreamingResponse: A streaming response containing the result of the update processing.
    """
    result = await dp.feed_webhook_update(bot, update, db=db_connector)
    return StreamingResponse(
        build_response_writer(bot, result), media_type="multipart/form-data"
    )


@router.post(
    "/api/telegram/save-user",
    tags=["Telegram Operations"],
    summary="Save or update Telegram user information",
)
async def save_telegram_user(user: TelegramUserCreate):
    """
    Save or update Telegram user information in the database.

    Args:
        user (TelegramUserCreate): The user information to save or update.

    Returns:
        dict: A dictionary with a success message.
    """
    try:
        telegram_user_db_connector.save_or_update_user(user.model_dump())
        return {"message": "Telegram user saved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving Telegram user: {str(e)}"
        )


@router.post(
    "/api/telegram/get-wallet-id/{telegram_id}",
    tags=["Telegram Operations"],
    summary="Get wallet ID for a Telegram user",
)
async def get_wallet_id(telegram_auth: TelegramUserAuth, telegram_id: str):
    """
    Retrieve the wallet ID associated with a Telegram user.

    Args:
        telegram_auth (TelegramUserAuth): Telegram authorization data or webapp init data.
        telegram_id (str): The Telegram user ID.

    Returns:
        dict: A dictionary containing the wallet ID or None if not found.
    """
    if telegram_auth.is_webapp:
        is_valid = check_webapp_signature(TELEGRAM_TOKEN, telegram_auth.raw)
    else:
        is_valid = check_telegram_authorization(TELEGRAM_TOKEN, telegram_auth.raw)

    if not is_valid:
        raise HTTPException(400, "Telegram auth data is invalid.")

    wallet_id = telegram_user_db_connector.get_wallet_id_by_telegram_id(telegram_id)
    return {"wallet_id": wallet_id}
