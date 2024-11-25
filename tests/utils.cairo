use alexandria_math::fast_power::fast_power;
use openzeppelin::token::erc20::interface::{IERC20Dispatcher, IERC20DispatcherTrait};
use snforge_std::cheatcodes::execution_info::caller_address::{
    start_cheat_caller_address, stop_cheat_caller_address
};
use snforge_std::{declare, ContractClassTrait, DeclareResultTrait, load, map_entry_address};
use spotnet::interfaces::{IVaultDispatcher, IVaultDispatcherTrait};
use starknet::{ContractAddress, contract_address_const, get_contract_address};
const HYPOTHETICAL_OWNER_ADDR: felt252 = 0x56789;


pub fn ERC20_MOCK_CONTRACT() -> ContractAddress {
    contract_address_const::<'erc20mock'>()
}

pub fn deploy_erc20_mock() -> ContractAddress {
    let contract = declare("SnakeERC20Mock").unwrap().contract_class();
    let name: ByteArray = "erc20 mock";
    let symbol: ByteArray = "ERC20MOCK";
    let initial_supply: u256 = 100 * fast_power(10, 18);
    let recipient: ContractAddress = get_contract_address();

    let mut calldata: Array<felt252> = array![];
    Serde::serialize(@name, ref calldata);
    Serde::serialize(@symbol, ref calldata);
    Serde::serialize(@initial_supply, ref calldata);
    Serde::serialize(@recipient, ref calldata);

    let (contract_addr, _) = contract.deploy_at(@calldata, ERC20_MOCK_CONTRACT()).unwrap();

    contract_addr
}


#[derive(Drop)]
pub struct VaultTestSuite {
    pub vault: IVaultDispatcher,
    pub token: IERC20Dispatcher,
    pub owner: ContractAddress,
}

pub fn setup_test_suite() -> VaultTestSuite {
    let owner: ContractAddress = HYPOTHETICAL_OWNER_ADDR.try_into().unwrap();
    let contract = declare("Vault").unwrap().contract_class();
    let token_address: ContractAddress = deploy_erc20_mock();

    let (vault_address, _) = contract
        .deploy(@array![owner.try_into().unwrap(), token_address.try_into().unwrap()])
        .unwrap();

    VaultTestSuite {
        vault: IVaultDispatcher { contract_address: vault_address },
        token: IERC20Dispatcher { contract_address: token_address },
        owner,
    }
}

pub fn setup_user(suite: @VaultTestSuite, user: ContractAddress, amount: u256) {
    // Transfer tokens to user
    (*suite.token).transfer(user, amount);

    start_cheat_caller_address(*suite.token.contract_address, user);
    (*suite.token).approve((*suite.vault).contract_address, amount);
    stop_cheat_caller_address(*suite.token.contract_address);
}

pub fn assert_vault_amount(
    vault: ContractAddress, user: ContractAddress, expected_amount: felt252
) {
    // Check remaining balance
    let balance_after_withdraw = load(
        vault, map_entry_address(selector!("amounts"), array![user.try_into().unwrap()].span()), 2,
    );
    assert(*balance_after_withdraw[0] == expected_amount, 'balance mismatch');
}
