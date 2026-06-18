"""
This module contains the transaction database configuration.
"""

import uuid
from typing import TypeVar

from web_app.db.models import Base, Transaction, TransactionStatus

from .base import DBConnector

ModelType = TypeVar("ModelType", bound=Base)


class TransactionDBConnector:
    """
    Provides database connection and operations management for the Transaction model.
    """

    def __init__(self, db_connector: DBConnector = None):
        from web_app.db.database import db_connector as default_db_connector

        self.db_connector = db_connector or default_db_connector

    def create_transaction(
        self, position_id: uuid.UUID, transaction_hash: str, status: TransactionStatus
    ) -> Transaction:
        """
        Creates a new transaction instance
        """
        transaction = Transaction(
            position_id=position_id,
            transaction_hash=transaction_hash,
            status=status,
        )
        transaction = self.db_connector.write_to_db(transaction)
        return transaction
