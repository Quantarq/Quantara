"""
This module loads environment variables and retrieves configuration settings for the Telegram bot.

It specifically retrieves the Telegram bot token and web app URL from environment variables.
"""

from os import getenv

from dotenv import load_dotenv

load_dotenv()

# Retrieve the Telegram bot token from environment variables
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
WEBAPP_URL = getenv("TELEGRAM_WEBAPP_URL", "https://quantara.xyz")


def parse_admin_ids(value: str) -> frozenset[int]:
    """Parse a comma-separated Telegram user ID allowlist."""
    admin_ids: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            admin_ids.add(int(item))
        except ValueError:
            continue
    return frozenset(admin_ids)


TELEGRAM_ADMIN_USER_IDS = parse_admin_ids(getenv("TELEGRAM_ADMIN_USER_IDS", ""))
