use openzeppelin::token::erc20::interface::{IERC20Dispatcher, IERC20DispatcherTrait};
use snforge_std::cheatcodes::execution_info::caller_address::{
    start_cheat_caller_address, stop_cheat_caller_address
};
use snforge_std::{load};
use spotnet::interfaces::{IVaultDispatcher, IVaultDispatcherTrait};

use starknet::{ContractAddress};
use super::utils::{setup_test_suite, setup_user, assert_vault_amount};

const MOCK_USER: felt252 = 0x1234;
const MOCK_USER_2: felt252 = 0x5678;

#[test]
fn test_deploy() {
    let suite = setup_test_suite();
    let token = load(suite.vault.contract_address, selector!("token"), 1,);

    assert!(*token[0] == suite.token.contract_address.try_into().unwrap(), "token not match");
}

#[test]
fn test_store_and_withdraw_liquidity_happy_path() {
    let suite = setup_test_suite();
    let user1: ContractAddress = MOCK_USER.try_into().unwrap();
    let amount: u256 = 100;

    setup_user(@suite, user1, amount);

    start_cheat_caller_address(suite.vault.contract_address, user1);
    suite.vault.store_liquidity(amount);
    stop_cheat_caller_address(suite.vault.contract_address);

    // Check stored balance
    assert_vault_amount(suite.vault.contract_address, user1, 100);

    // Withdraw 50
    start_cheat_caller_address(suite.vault.contract_address, user1);
    suite.vault.withdraw_liquidity(50);
    stop_cheat_caller_address(suite.vault.contract_address);

    // Check remaining balance
    assert_vault_amount(suite.vault.contract_address, user1, 50);
}


#[test]
fn test_store_and_withdraw_multiple_users() {
    let suite = setup_test_suite();
    let user1: ContractAddress = MOCK_USER.try_into().unwrap();
    let user2: ContractAddress = MOCK_USER_2.try_into().unwrap();

    let user1_amount: u256 = 100;
    let user2_amount: u256 = 150;

    // Setup both users
    setup_user(@suite, user1, user1_amount);
    setup_user(@suite, user2, user2_amount);

    // User 1 stores and withdraws
    start_cheat_caller_address(suite.vault.contract_address, user1);
    suite.vault.store_liquidity(user1_amount);
    suite.vault.withdraw_liquidity(30);
    stop_cheat_caller_address(suite.vault.contract_address);

    // User 2 stores and withdraws
    start_cheat_caller_address(suite.vault.contract_address, user2);
    suite.vault.store_liquidity(user2_amount);
    suite.vault.withdraw_liquidity(50);
    stop_cheat_caller_address(suite.vault.contract_address);

    // Check final balances of both users
    assert_vault_amount(suite.vault.contract_address, user1, 70);
    assert_vault_amount(suite.vault.contract_address, user2, 100);
}

#[test]
#[should_panic(expected: ('Approved amount insufficient',))]
fn test_insufficient_allowance() {
    let suite = setup_test_suite();
    let user1: ContractAddress = MOCK_USER.try_into().unwrap();
    let user_amount: u256 = 100;
    let approved_amount: u256 = 50; // less than needed

    suite.token.transfer(user1, user_amount);

    start_cheat_caller_address(suite.token.contract_address, user1);
    suite.token.approve(suite.vault.contract_address, approved_amount);
    stop_cheat_caller_address(suite.token.contract_address);

    // Should fail when trying to store more than approved
    start_cheat_caller_address(suite.vault.contract_address, user1);
    suite.vault.store_liquidity(user_amount);
    stop_cheat_caller_address(suite.vault.contract_address);
}

#[test]
#[should_panic(expected: ('Not enough tokens to withdraw',))]
fn test_insufficient_balance_withdraw() {
    let suite = setup_test_suite();
    let user1: ContractAddress = MOCK_USER.try_into().unwrap();

    start_cheat_caller_address(suite.vault.contract_address, user1);
    suite.vault.withdraw_liquidity(100);
    stop_cheat_caller_address(suite.vault.contract_address);
}
