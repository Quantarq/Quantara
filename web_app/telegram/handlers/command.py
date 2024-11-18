"""
This module handles command-related functionality for the Telegram bot.

It defines the command router and the behavior for the /start command.
"""

from aiogram import Router, F
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from ..markups import launch_main_web_app_kb
from ..texts import NOTIFICATIONS_ENABLED_MESSAGE, WELCOME_MESSAGE
from web_app.db.crud import TelegramUserDBConnector

telegram_db = TelegramUserDBConnector()

# Create a router for handling commands
cmd_router = Router()


@cmd_router.message(
    CommandStart(
        deep_link=True,
        deep_link_encoded=True,
        magic=F.args.startswith("subscribe:"),
    )
)
async def start_cmd(message: Message, command: CommandObject):
    """
    Handle the /start command with a deep link for subscription.

    Args:
        message (Message): The incoming message containing the command.
        command (CommandObject): The command object containing the command arguments.

    Returns:
        Message: Sends a message indicating notifications are enabled, 
            along with a button to launch the web app.
    """
    _, wallet_id = command.args.split(":", maxsplit=1)
    telegram_db.set_notification_allowed(
        telegram_id=message.from_user.id, wallet_id=wallet_id
    )
    return message.answer(
        NOTIFICATIONS_ENABLED_MESSAGE, reply_markup=launch_main_web_app_kb
    )


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
