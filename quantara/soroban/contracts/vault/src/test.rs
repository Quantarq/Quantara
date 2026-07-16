#![cfg(test)]

use super::*;
use soroban_sdk::{Env, testutils::Address as _, Address};

#[test]
fn test_deposit() {
    let env = Env::default();
    env.mock_all_auths();
    
    let contract_id = env.register_contract(None, VaultContract);
    let client = VaultContractClient::new(&env, &contract_id);
    
    let user = Address::generate(&env);
    let token = Address::generate(&env);
    
    let deposited = client.deposit(&user, &token, &500);
    assert_eq!(deposited, 500);
}
