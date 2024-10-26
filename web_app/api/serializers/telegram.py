from pydantic import BaseModel


class TelegramUserCreate(BaseModel):
    telegram_id: str
    username: str | None
    first_name: str | None
    last_name: str | None
    photo_url: str | None

    wallet_id: str | None


class TelegramUserAuth(BaseModel):
    raw: str | dict
    is_webapp: bool
