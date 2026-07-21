//! cargo-fuzz harness for RewardsContract entry-points.
//!
//! Validates:
//! - accrue: non-negative accrual always succeeds; balance increases correctly.
//! - claim: claimed amount equals pending balance; balance resets to 0.
//! - pending_rewards: always returns >= 0.

#![no_main]

use libfuzzer_sys::fuzz_target;
use soroban_sdk::{testutils::Address as _, Address, Env};
use rewards::RewardsContractClient;

fuzz_target!(|data: &[u8]| {
    if data.len() < 16 {
        return;
    }
    let accrual_a = i64::from_le_bytes(data[..8].try_into().unwrap()).unsigned_abs() as i128;
    let accrual_b = i64::from_le_bytes(data[8..16].try_into().unwrap()).unsigned_abs() as i128;

    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register(rewards::RewardsContract, ());
    let client = RewardsContractClient::new(&env, &contract_id);
    let user = Address::generate(&env);

    // Accrue twice; pending should be the sum.
    client.accrue(&user, &accrual_a);
    client.accrue(&user, &accrual_b);

    let pending = client.pending_rewards(&user);
    assert!(pending >= 0, "pending_rewards returned negative: {}", pending);

    let expected = accrual_a + accrual_b;
    assert_eq!(pending, expected, "pending mismatch: got {}, expected {}", pending, expected);

    // Claim: should return full pending amount and reset to 0.
    let claimed = client.claim(&user);
    assert_eq!(claimed, expected, "claimed={} != expected={}", claimed, expected);
    assert_eq!(
        client.pending_rewards(&user),
        0,
        "pending after claim should be 0"
    );
});
