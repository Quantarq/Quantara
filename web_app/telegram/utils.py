"""
This module contains utility functions for the Telegram bot.

It includes functions for building response writers for webhook responses.
"""
import hashlib
import hmac
import secrets
import time
from typing import Dict, Optional

from aiogram import Bot
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import InputFile
from aiohttp import MultipartWriter


def check_telegram_authorization(token: str, auth_data: dict, expired: int = None) -> bool:
    """
    Verify the Telegram authorization data.

    Args:
        token (str): The bot's token used for verification.
        auth_data (dict): The authorization data received from Telegram, 
                          including the hash and auth_date.

    Raises:
        Exception: If the data is not from Telegram or if it is outdated.

    Returns:
        dict: The verified authorization data.
    """
    check_hash = auth_data.get("hash")
    if not check_hash:
        return False
    data_check_arr = [f"{key}={value}" for key, value in auth_data.items() if key != "hash"]
    data_check_arr.sort()
    data_check_string = "\n".join(data_check_arr)

    secret_key = hashlib.sha256(token.encode()).digest()
    hash_value = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if hash_value != check_hash:
        return False

    if expired and (int(time.time()) - auth_data["auth_date"]) > expired:
        return False

    return True


def build_response_writer(
    bot: Bot, result: Optional[TelegramMethod[TelegramType]]
) -> MultipartWriter:
    """
    Build a MultipartWriter for sending a response to a Telegram webhook.

    Args:
        bot (Bot): The instance of the Bot to use for handled requests.
        result (Optional[TelegramMethod[TelegramType]]): The result of a Telegram method call.

    Returns:
        MultipartWriter: A writer for the multipart/form-data request.
    """
    writer = MultipartWriter(
        "form-data",
        boundary=f"webhookBoundary{secrets.token_urlsafe(16)}",
    )
    if not result:
        return writer

    # Append the API method to the writer
    payload = writer.append(result.__api_method__)
    payload.set_content_disposition("form-data", name="method")

    files: Dict[str, InputFile] = {}
    for key, value in result.model_dump(warnings=False).items():
        value = bot.session.prepare_value(value, bot=bot, files=files)
        if not value:
            continue
        payload = writer.append(value)
        payload.set_content_disposition("form-data", name=key)

    for key, value in files.items():
        payload = writer.append(value.read(bot))
        payload.set_content_disposition(
            "form-data",
            name=key,
            filename=value.filename or key,
        )

    return writer
