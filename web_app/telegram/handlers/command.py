"""
This module handles command-related functionality for the Telegram bot.

It defines the command router and the behavior for the /start command.
"""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ..markups import launch_main_web_app_kb
from ..texts import WELCOME_MESSAGE

# Create a router for handling commands
cmd_router = Router()


@cmd_router.message(CommandStart())
async def start_cmd(message: Message):
    """
    Handle the /start command.

    Args:
        message (Message): The incoming message containing the command.

    Returns:
        None: Sends a welcome message with a button to launch the web app.
    """
    return message.answer(WELCOME_MESSAGE, reply_markup=launch_main_web_app_kb)
