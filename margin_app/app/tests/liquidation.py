"""Tests for LiquidationCRUD in spotnet/margin_app/app/crud/liquidation.py"""

import pytest
from app.crud.liquidation import LiquidationCRUD
from app.models.liquidation import Liquidation

@pytest.fixture
def mock_session():
    class MockSession:
        def _init_(self):
            self.data = []

        def add(self, obj):
            self.data.append(obj)

        def commit(self):
            pass

        def query(self, model):
            class Query:
                def _init_(self, data):
                    self.data = data
                    self.filtered = []

                def filter_by(self, **kwargs):
                    self.filtered = [
                        d for d in self.data
                        if all(getattr(d, key, None) == value for key, value in kwargs.items())
                    ]
                    return self

                def first(self):
                    return self.filtered[0] if self.filtered else None

            return Query(self.data)
    return MockSession()

def test_create_liquidation_success(mock_session):
    """Test creating a liquidation record with valid data."""
    liquidation_data = {"id": 1, "amount": 1000, "status": "pending"}
    liquidation = LiquidationCRUD.create(mock_session, liquidation_data)
    assert liquidation is not None
    assert liquidation.id == 1

def test_create_liquidation_failure(mock_session):
    """Test that creating a liquidation record with invalid data raises an error."""
    liquidation_data = {"amount": -500}  # Invalid data: negative amount
    with pytest.raises(ValueError):
        LiquidationCRUD.create(mock_session, liquidation_data)

def test_get_liquidation_success(mock_session):
    """Test retrieving an existing liquidation record."""
    # Create and add a liquidation instance to the session.
    liquidation_instance = Liquidation(id=1, amount=1000, status="pending")
    mock_session.add(liquidation_instance)
    liquidation = LiquidationCRUD.get(mock_session, 1)
    assert liquidation is not None
    assert liquidation.id == 1

def test_get_liquidation_not_found(mock_session):
    """Test retrieving a non-existent liquidation record returns None."""
    liquidation = LiquidationCRUD.get(mock_session, 999)
    assert liquidation is None