from pydantic import BaseModel, validator
from web_app.contract_tools.constants import TokenParams


class PositionFormData(BaseModel):
    """
    Pydantic model for the form data
    """

    wallet_id: str
    token_symbol: str
    amount: str
    multiplier: int

    @validator("token_symbol")
    def validate_token_symbol(cls, value: str) -> str:
        """
        Get the token symbol based on the input address
        :param value: str
        :return: str
        """
        return TokenParams.get_token_symbol(value)
