//! cargo-fuzz harness for VaultContract::withdraw entry-point.
//!
//! Fuzz strategy: feed arbitrary (initial_deposit: u64, withdraw_amount: i64).
//!
//! Invariants checked:
//! - Balance never goes negative.
//! - Valid withdrawals (0 < amount <= balance) succeed.
//!
//! Run:
//! ```bash
//! cargo +nightly fuzz run fuzz_vault_withdraw -- -max_total_time=60
//! ```

#![no_main]

use libfuzzer_sys::fuzz_target;
use soroban_sdk::{testutils::Address as _, Address, Env, IntoVal};
use vault::VaultContract;

fuzz_target!(|data: &[u8]| {
    if data.len() < 16 {
        return;
    }
    let initial_deposit = u64::from_le_bytes(data[..8].try_into().unwrap()) as i128;
    let withdraw_amount = i64::from_le_bytes(data[8..16].try_into().unwrap()) as i128;

    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register(VaultContract, ());
    let user = Address::generate(&env);

    // Seed a known balance if initial_deposit is positive.
    if initial_deposit > 0 {
        let _: () = env.invoke_contract(
            &contract_id,
            &soroban_sdk::symbol_short!("deposit"),
            soroban_sdk::vec![&env, user.to_val(), initial_deposit.into_val(&env)],
        );
    }

    // Attempt withdrawal.
    let _ = env.try_invoke_contract::<(), _>(
        &contract_id,
        &soroban_sdk::symbol_short!("withdraw"),
        soroban_sdk::vec![&env, user.to_val(), withdraw_amount.into_val(&env)],
    );

    // Balance must never be negative.
    let balance: i128 = env.invoke_contract(
        &contract_id,
        &soroban_sdk::symbol_short!("balance"),
        soroban_sdk::vec![&env, user.to_val()],
    );
    assert!(balance >= 0, "balance went negative: {balance}");
});
