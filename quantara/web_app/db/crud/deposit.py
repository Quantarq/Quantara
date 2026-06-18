"""
This module contains the deposit database configuration.
"""

import logging
from decimal import Decimal
from typing import TypeVar

from web_app.db.models import Base, User, Vault

from .base import DBConnector

logger = logging.getLogger(__name__)
ModelType = TypeVar("ModelType", bound=Base)


class DepositDBConnector:
    """
    Provides database connection and operations management for the Vault model.
    """

    def __init__(self, db_connector: DBConnector = None):
        from web_app.db.database import db_connector as default_db_connector

        self.db_connector = db_connector or default_db_connector

    def create_vault(self, user: User, symbol: str, amount: str) -> Vault:
        """
        Creates a new vault instance

        :param user: A user model instance
        :param symbol: Token symbol or address
        :param amount: An amount in string

        :return: Vault
        """
        vault = Vault(user_id=user.id, symbol=symbol, amount=amount)
        self.db_connector.write_to_db(vault)
        return vault

    def get_vault(self, wallet_id: str, symbol: str) -> Vault | None:
        """
        Gets a user vault instance for a symbol

        :param wallet_id: Wallet id of user
        :param symbol: Token symbol or address

        :return: Vault or None
        """
        with self.db_connector.Session() as db:
            user = self.db_connector.get_object_by_field(User, "wallet_id", wallet_id)
            if not user:
                logger.error(f"User with wallet id {wallet_id} not found")
                return None
            vault = db.query(Vault).filter_by(user_id=user.id, symbol=symbol).first()
        return vault

    def add_vault_balance(self, wallet_id: str, symbol: str, amount: str) -> Vault:
        """
        Adds balance to user vault for token symbol

        :param wallet_id: Wallet id of user
        :param symbol: Token symbol or address
        :param amount: An amount in string

        :return: Updated Vault instance
        """
        vault = self.get_vault(wallet_id, symbol)
        if not vault:
            raise ValueError("Vault not found")
        with self.db_connector.Session() as db:
            new_amount = Decimal(vault.amount) + Decimal(amount)
            db.query(Vault).filter_by(id=vault.id).update(amount=str(new_amount))
            db.commit()
            vault = self.get_vault(wallet_id, symbol)
        return vault

    def get_vault_balance(self, wallet_id: str, symbol: str) -> str | None:
        """
        Get the balance of a vault for a particular token symbol

        :param wallet_id: The wallet id of the user
        :param symbol: Token symbol or address

        :returns: str or None
        """
        vault = self.get_vault(wallet_id, symbol)
        return vault.amount if vault else None
