"""
This module contains the fixtures for the tests.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from web_app.api.main import app
from web_app.db.crud import (
    DBConnector,
    PositionDBConnector,
    UserDBConnector,
)
from web_app.db.database import get_database


@pytest.fixture(scope="module")
def client() -> None:
    """
    TestClient with setted mock db connection
    :return: None
    """

    mock_db_connector = MagicMock(spec=DBConnector)
    app.dependency_overrides[get_database] = lambda: mock_db_connector

    with TestClient(app=app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def mock_db_connector() -> None:
    """
    Mock DBConnector
    :return: None
    """
    mock_connector = MagicMock(spec=DBConnector)
    yield mock_connector


@pytest.fixture(scope="module")
def mock_user_db_connector() -> None:
    """
    Mock for UserDBConnector
    :return: None
    """
    mock_user_connector = MagicMock(spec=UserDBConnector)
    yield mock_user_connector


@pytest.fixture(scope="module")
def mock_position_db_connector() -> None:
    """
    Mock for PositionDBConnector
    :return: None
    """
    mock_position_connector = MagicMock(spec=PositionDBConnector)
    yield mock_position_connector
