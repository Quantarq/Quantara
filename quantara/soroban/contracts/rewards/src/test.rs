#![cfg(test)]

use super::*;
use soroban_sdk::{Env, testutils::Address as _, Address};

#[test]
fn test_claim() {
    let env = Env::default();
    env.mock_all_auths();
    
    let contract_id = env.register_contract(None, RewardsContract);
    let client = RewardsContractClient::new(&env, &contract_id);
    
    let user = Address::generate(&env);
    
    let claimed = client.claim(&user);
    assert_eq!(claimed, 100);
}
