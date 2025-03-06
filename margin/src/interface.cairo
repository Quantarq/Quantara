use starknet::ContractAddress;
use crate::types::{TokenAmount, PositionParameters};

#[starknet::interface]
pub trait IMargin<TContractState> {
    fn deposit(ref self: TContractState, token: ContractAddress, amount: TokenAmount);
    fn withdraw(ref self: TContractState, token: ContractAddress, amount: TokenAmount);

    // TODO: Add Ekubo data for swap
    fn open_margin_position(ref self: TContractState, position_parameters: PositionParameters);
    fn close_position(ref self: TContractState);

    fn liquidate(ref self: TContractState, user: ContractAddress);
}

#[starknet::interface]
pub trait IERC20MetadataForPragma<TState> {
    fn name(self: @TState) -> ByteArray;
    fn symbol(self: @TState) -> felt252;
    fn decimals(self: @TState) -> felt252;
}
