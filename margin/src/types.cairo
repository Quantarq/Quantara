use starknet::ContractAddress;

pub type TokenAmount = u256;
pub type Timestamp = u128;

#[derive(Serde, Drop)]
pub struct PositionParameters {
    pub initial_token: ContractAddress,
    pub debt_token: ContractAddress, 
    pub amount: TokenAmount,
}

#[derive(Serde, starknet::Store)]
pub struct Position {
    pub initial_token: ContractAddress,
    pub traded_token: ContractAddress,
    pub traded_amount: TokenAmount,
    pub debt: TokenAmount,
    pub is_open: bool,
    pub open_time: Timestamp,
}
