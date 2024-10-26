"""
This module provides asynchronous database operations for managing TelegramUser and other models
using SQLAlchemy in a FastAPI application context. It includes functionalities for creating, 
reading, updating, and deleting records in the database.
"""
import logging
import uuid
from typing import Type, TypeVar
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from web_app.db.database import SQLALCHEMY_DATABASE_URL
from web_app.db.models import Base, Position, Status, TelegramUser, User

logger = logging.getLogger(__name__)
ModelType = TypeVar("ModelType", bound=Base)  # type: ignore


class AsyncDBConnector:
    """
    Provides asynchronous database connection and operations management using SQLAlchemy
    in a FastAPI application context.
    """

    def __init__(self, db_url: str = SQLALCHEMY_DATABASE_URL):
        """
        Initialize the database connection and session factory.
        :param db_url: str = None
        """
        self.engine = create_async_engine(db_url)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def write_to_db(self, obj: ModelType = None) -> ModelType:
        """
        Writes an object to the database asynchronously. Rolls back the transaction if there's an error.
        :param obj: ModelType = None
        :raise SQLAlchemyError: If the database operation fails.
        :return: ModelType - the updated object
        """
        async with self.async_session() as session:
            async with session.begin():
                try:
                    session.add(obj)
                    await session.commit()
                    await session.refresh(obj)
                    return obj
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e

    async def get_object(
        self, model: Type[ModelType] = None, obj_id: uuid = None
    ) -> ModelType | None:
        """
        Retrieves an object by its ID from the database asynchronously.
        :param: model: type[Base] = None
        :param: obj_id: uuid = None
        :return: Base | None
        """
        async with self.async_session() as session:
            result = await session.execute(select(model).filter(model.id == obj_id))
            return result.scalar_one_or_none()

    async def get_object_by_field(
        self, model: Type[ModelType] = None, field: str = None, value: str = None
    ) -> ModelType | None:
        """
        Retrieves an object by a specified field from the database asynchronously.
        :param model: type[Base] = None
        :param field: str = None
        :param value: str = None
        :return: Base | None
        """
        async with self.async_session() as session:
            result = await session.execute(
                select(model).filter(getattr(model, field) == value)
            )
            return result.scalar_one_or_none()

    async def delete_object(
        self, model: Type[ModelType] = None, obj_id: uuid = None
    ) -> None:
        """
        Delete an object by its ID from the database asynchronously. Rolls back if the operation fails.
        :param model: type[Base] = None
        :param obj_id: uuid = None
        :return: None
        :raise SQLAlchemyError: If the database operation fails
        """
        async with self.async_session() as session:
            async with session.begin():
                try:
                    obj = await session.execute(
                        select(model).filter(model.id == obj_id)
                    )
                    obj = obj.scalar_one_or_none()
                    if obj:
                        await session.delete(obj)
                        await session.commit()
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e


class AsyncTelegramUserDBConnector(AsyncDBConnector):
    """
    Provides asynchronous database connection and operations management for the TelegramUser model.
    """

    async def get_user_by_telegram_id(self, telegram_id: str) -> TelegramUser | None:
        """
        Retrieves a TelegramUser by their Telegram ID asynchronously.
        :param telegram_id: str
        :return: TelegramUser | None
        """
        return await self.get_object_by_field(TelegramUser, "telegram_id", telegram_id)

    async def get_wallet_id_by_telegram_id(self, telegram_id: str) -> str | None:
        """
        Retrieves the wallet ID of a TelegramUser by their Telegram ID asynchronously.
        :param telegram_id: str
        :return: str | None
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        return user.wallet_id if user else None

    async def create_telegram_user(self, user_data: dict) -> TelegramUser:
        """
        Creates a new TelegramUser in the database asynchronously.
        :param user_data: dict
        :return: TelegramUser
        """
        telegram_user = TelegramUser(**user_data)
        return await self.write_to_db(telegram_user)

    async def update_telegram_user(self, telegram_id: str, user_data: dict) -> None:
        """
        Updates a TelegramUser in the database asynchronously.
        :param telegram_id: str
        :param user_data: dict
        :return: None
        """
        async with self.get_session() as session:
            stmt = (
                update(TelegramUser)
                .where(TelegramUser.telegram_id == telegram_id)
                .values(**user_data)
            )
            await session.execute(stmt)
            await session.commit()

    async def save_or_update_user(self, user_data: dict) -> TelegramUser:
        """
        Saves a new TelegramUser or updates an existing one asynchronously.
        :param user_data: dict
        :return: TelegramUser
        """
        telegram_id = user_data.get("telegram_id")
        existing_user = await self.get_user_by_telegram_id(telegram_id)

        if existing_user:
            await self.update_telegram_user(telegram_id, user_data)
            return await self.get_user_by_telegram_id(telegram_id)
        else:
            return await self.create_telegram_user(user_data)

    async def delete_telegram_user(self, telegram_id: str) -> None:
        """
        Deletes a TelegramUser from the database asynchronously.
        :param telegram_id: str
        :return: None
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        if user:
            await self.delete_from_db(user)
