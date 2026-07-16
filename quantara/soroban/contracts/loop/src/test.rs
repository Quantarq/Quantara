#![cfg(test)]

use super::*;
use soroban_sdk::{Env, testutils::Address as _, Address};

#[test]
fn test_loop_position() {
    let env = Env::default();
    env.mock_all_auths();
    
    let contract_id = env.register_contract(None, LoopContract);
    let client = LoopContractClient::new(&env, &contract_id);
    
    let user = Address::generate(&env);
    let token = Address::generate(&env);
    
    let position = client.loop_position(&user, &token, &100, &3);
    assert_eq!(position, 300);
}
