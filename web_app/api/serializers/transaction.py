from pydantic import BaseModel, Field, validator


class ApproveData(BaseModel):
    to_address: str = Field(
        ..., description="Address of the recipient in string format"
    )
    spender: str = Field(..., description="Spender address in string format")
    amount: str = Field(..., description="Amount of tokens to approve as a string")

    @validator("to_address", "spender", "amount", pre=True, always=True)
    def convert_int_to_str(cls, v):
        return str(v)


class PoolKey(BaseModel):
    token0: str
    token1: str
    fee: str
    tick_spacing: str
    extension: str

    @validator(
        "token0", "token1", "fee", "tick_spacing", "extension", pre=True, always=True
    )
    def convert_int_to_str(cls, v):
        return str(v)


class DepositData(BaseModel):
    token: str
    amount: str
    multiplier: str

    @validator("token", "amount", "multiplier", pre=True, always=True)
    def convert_int_to_str(cls, v):
        return str(v)


class LoopLiquidityData(BaseModel):
    caller: str
    pool_price: int  # Assuming this should remain an integer
    pool_key: PoolKey
    deposit_data: DepositData

    @validator("caller", pre=True, always=True)
    def convert_caller_to_str(cls, v):
        return str(v)


class TransactionDataResponse(BaseModel):
    approve_data: ApproveData
    loop_liquidity_data: LoopLiquidityData


class TransactionDataRequest(BaseModel):
    token: str = Field(..., description="Token name for the transaction")
    multiplier: int = Field(..., description="Multiplier for the transaction")
    amount: str = Field(..., description="Amount to deposit as a string")
