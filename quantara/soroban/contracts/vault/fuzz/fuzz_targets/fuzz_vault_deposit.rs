//! cargo-fuzz harness for VaultContract::deposit entry-point.
//!
//! Fuzz strategy: feed arbitrary (amount: i64) as input.
//!
//! Invariants checked:
//! - Positive amounts must succeed (no panic).
//! - After a successful deposit, balance equals the deposited amount.
//! - Non-positive amounts may panic (documented assertion); we just
//!   ensure no memory safety issues occur.
//!
//! Run:
//! ```bash
//! cargo +nightly fuzz run fuzz_vault_deposit -- -max_total_time=60
//! ```

#![no_main]

use libfuzzer_sys::fuzz_target;
use soroban_sdk::{testutils::Address as _, Address, Env};
use vault::VaultContract;

fuzz_target!(|data: &[u8]| {
    if data.len() < 8 {
        return;
    }
    let amount = i64::from_le_bytes(data[..8].try_into().unwrap()) as i128;

    let env = Env::default();
    env.mock_all_auths();

    let contract_id = env.register(VaultContract, ());
    let user = Address::generate(&env);

    // Invoke deposit directly via the registered contract.
    let result = env.try_invoke_contract::<(), _>(
        &contract_id,
        &soroban_sdk::symbol_short!("deposit"),
        soroban_sdk::vec![&env, user.to_val(), amount.into()],
    );

    if amount > 0 {
        // Must succeed — any error here is a bug.
        assert!(
            result.is_ok(),
            "deposit with positive amount={amount} returned error"
        );

        // Balance must equal the deposited amount.
        let balance: i128 = env
            .invoke_contract(
                &contract_id,
                &soroban_sdk::symbol_short!("balance"),
                soroban_sdk::vec![&env, user.to_val()],
            );
        assert_eq!(balance, amount, "balance mismatch after deposit");
    }
    // Non-positive: may return error (documented); no further assertion.
});
