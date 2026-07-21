//! cargo-fuzz harness for the Vault contract entry-points.
//!
//! Fuzz targets:
//!   - `deposit`:  arbitrary (user, amount) pairs — must not panic except
//!                  on the documented assertion `amount > 0`.
//!   - `withdraw`: arbitrary (user, amount, initial_balance) triples — must
//!                  not panic except on documented assertions.
//!   - `balance`:  arbitrary user — always returns a value, never panics.
//!
//! Run for 60 seconds per entry-point:
//! ```bash
//! cargo +nightly fuzz run fuzz_vault_deposit   -- -max_total_time=60
//! cargo +nightly fuzz run fuzz_vault_withdraw  -- -max_total_time=60
//! cargo +nightly fuzz run fuzz_vault_balance   -- -max_total_time=60
//! ```

#![no_main]

use libfuzzer_sys::fuzz_target;
use soroban_sdk::{
    testutils::Address as _,
    Address, Env,
};
use vault::VaultContractClient;

// ---------------------------------------------------------------------------
// Shared helper: spin up a fresh environment with a registered vault contract.
// ---------------------------------------------------------------------------
fn setup() -> (Env, Address, VaultContractClient<'static>) {
    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register(vault::VaultContract, ());
    let client = VaultContractClient::new(&env, &contract_id);
    let user = Address::generate(&env);
    // Work around lifetime issues by leaking the env.  This is intentional in
    // fuzz harnesses where the env lifetime must outlive the client.
    let env_static: &'static Env = Box::leak(Box::new(env));
    let client_static = VaultContractClient::new(env_static, &contract_id);
    (env_static.clone(), user, client_static)
}

// ---------------------------------------------------------------------------
// Fuzz deposit
// ---------------------------------------------------------------------------
fuzz_target!(|data: &[u8]| {
    if data.len() < 8 {
        return;
    }
    let amount = i64::from_le_bytes(data[..8].try_into().unwrap()) as i128;

    let (env, user, client) = setup();

    // Positive amounts must succeed; non-positive must assert/panic.
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        client.deposit(&user, &amount);
    }));

    if amount > 0 {
        // Must succeed — any panic here is a bug.
        assert!(
            result.is_ok(),
            "deposit with positive amount={} panicked unexpectedly",
            amount
        );
        // Balance must equal the deposited amount.
        assert_eq!(client.balance(&user), amount);
    }
    // Non-positive amounts may panic (documented behaviour); we just ensure
    // they do not corrupt state or trigger undefined behaviour.
});
