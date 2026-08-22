"""
This module contains the deposit database configuration.
"""

import logging
import uuid
from decimal import Decimal
from typing import TypeVar

from sqlalchemy import Numeric, cast, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from web_app.db.models import Base, User, Vault

from .base import DBConnector
from web_app.utils.logger import get_logger

logger = get_logger(__name__)
ModelType = TypeVar("ModelType", bound=Base)


class DepositDBConnector(DBConnector):
    """
    Provides database connection and operations management for the Vault model.
    """

    def upsert_vault(self, user_id: uuid.UUID, symbol: str, amount: str) -> Vault:
        """
        Atomically inserts a new vault row or adds to the existing balance.

        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE so that concurrent
        calls for the same (user_id, symbol) never lose updates.

        :param user_id: UUID of the user
        :param symbol: Token symbol or address
        :param amount: Amount to add (as string)

        :return: Vault instance (existing row updated or newly inserted)
        """
        with self.Session() as db:
            stmt = (
                pg_insert(Vault)
                .values(user_id=user_id, symbol=symbol, amount=amount)
                .on_conflict_do_update(
                    constraint="uq_vault_user_symbol",
                    set_={
                        "amount": cast(Vault.amount, Numeric)
                        + cast(amount, Numeric),
                        "updated_at": func.now(),
                    },
                )
                .returning(Vault)
            )
            result = db.execute(stmt)
            vault = result.scalar_one()
            db.commit()
            db.refresh(vault)
            return vault

    def create_vault(self, user: User, symbol: str, amount: str) -> Vault:
        """
        Creates a new vault instance or updates existing balance atomically.

        :param user: A user model instance
        :param symbol: Token symbol or address
        :param amount: An amount in string

        :return: Vault
        """
        return self.upsert_vault(user.id, symbol, amount)

    def get_vault(self, wallet_id: str, symbol: str) -> Vault | None:
        """
        Gets a user vault instance for a symbol

        :param wallet_id: Wallet id of user
        :param symbol: Token symbol or address

        :return: Vault or None
        """
        with self.Session() as db:
            user = self.get_object_by_field(User, "wallet_id", wallet_id)
            if not user:
                logger.error("db_get_vault_user_not_found", wallet_id=wallet_id)
                return None
            vault = db.query(Vault).filter_by(user_id=user.id, symbol=symbol).first()
        return vault

    def add_vault_balance(self, wallet_id: str, symbol: str, amount: str) -> Vault:
        """
        Adds balance to user vault for token symbol atomically.

        :param wallet_id: Wallet id of user
        :param symbol: Token symbol or address
        :param amount: An amount in string

        :return: Updated Vault instance
        """
        user = self.get_object_by_field(User, "wallet_id", wallet_id)
        if not user:
            raise ValueError("User not found")
        return self.upsert_vault(user.id, symbol, amount)

    def get_vault_balance(self, wallet_id: str, symbol: str) -> str | None:
        """
        Get the balance of a vault for a particular token symbol

        :param wallet_id: The wallet id of the user
        :param symbol: Token symbol or address

        :returns: str or None
        """
        vault = self.get_vault(wallet_id, symbol)
        return vault.amount if vault else None
