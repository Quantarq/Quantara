import pytest
from pydantic import ValidationError

from web_app.api.serializers.position import AddPositionDepositData, PositionFormData
from web_app.db.models import Position, SUPPORTED_POSITION_TOKENS


def test_position_form_data_normalizes_supported_token_symbol():
    form = PositionFormData(
        wallet_id="GABC",
        token_symbol="usdc",
        amount="100",
        multiplier="2",
    )

    assert form.token_symbol == "USDC"


def test_position_form_data_rejects_unsupported_token_symbol():
    with pytest.raises(ValidationError):
        PositionFormData(
            wallet_id="GABC",
            token_symbol="DOGE",
            amount="100",
            multiplier="2",
        )


def test_extra_deposit_data_rejects_unsupported_token_symbol():
    with pytest.raises(ValidationError):
        AddPositionDepositData(amount="50", token_symbol="DOGE")


def test_position_model_has_supported_token_check_constraint():
    constraints = {constraint.name: constraint for constraint in Position.__table__.constraints}

    constraint = constraints["ck_position_token_symbol_supported"]
    sql = str(constraint.sqltext)

    for token in SUPPORTED_POSITION_TOKENS:
        assert token in sql
    assert "DOGE" not in sql