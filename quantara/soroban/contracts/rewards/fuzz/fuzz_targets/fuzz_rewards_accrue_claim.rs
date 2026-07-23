//! cargo-fuzz harness for RewardsContract::accrue and claim entry-points.
//!
//! Invariants checked:
//! - pending_rewards is always >= 0.
//! - After two accruals, pending == sum of accruals.
//! - After claim, pending resets to 0.
//!
//! Run:
//! ```bash
//! cargo +nightly fuzz run fuzz_rewards_accrue_claim -- -max_total_time=60
//! ```

#![no_main]

use libfuzzer_sys::fuzz_target;
use soroban_sdk::{testutils::Address as _, Address, Env, IntoVal, Symbol};
use rewards::RewardsContract;

fuzz_target!(|data: &[u8]| {
    if data.len() < 16 {
        return;
    }
    // Use unsigned abs to keep accruals non-negative.
    let accrual_a = i64::from_le_bytes(data[..8].try_into().unwrap()).unsigned_abs() as i128;
    let accrual_b = i64::from_le_bytes(data[8..16].try_into().unwrap()).unsigned_abs() as i128;

    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register(RewardsContract, ());
    let user = Address::generate(&env);

    // Accrue twice.
    let _: () = env.invoke_contract(
        &contract_id,
        &soroban_sdk::symbol_short!("accrue"),
        soroban_sdk::vec![&env, user.to_val(), accrual_a.into_val(&env)],
    );
    let _: () = env.invoke_contract(
        &contract_id,
        &soroban_sdk::symbol_short!("accrue"),
        soroban_sdk::vec![&env, user.to_val(), accrual_b.into_val(&env)],
    );

    // Check pending equals sum.
    let pending: i128 = env.invoke_contract(
        &contract_id,
        &Symbol::new(&env, "pending_rewards"),
        soroban_sdk::vec![&env, user.to_val()],
    );
    assert!(pending >= 0, "pending_rewards negative: {pending}");
    let expected = accrual_a + accrual_b;
    assert_eq!(pending, expected, "pending={pending} expected={expected}");

    // Claim and verify reset.
    let claimed: i128 = env.invoke_contract(
        &contract_id,
        &soroban_sdk::symbol_short!("claim"),
        soroban_sdk::vec![&env, user.to_val()],
    );
    assert_eq!(claimed, expected, "claimed={claimed} expected={expected}");

    let after: i128 = env.invoke_contract(
        &contract_id,
        &Symbol::new(&env, "pending_rewards"),
        soroban_sdk::vec![&env, user.to_val()],
    );
    assert_eq!(after, 0, "pending after claim should be 0, got {after}");
});
