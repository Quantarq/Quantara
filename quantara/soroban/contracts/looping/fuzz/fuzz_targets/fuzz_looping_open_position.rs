//! cargo-fuzz harness for LoopingContract::open_position entry-point.
//!
//! Invariants checked:
//! - Valid inputs (collateral > 0, leverage 100–500) must succeed.
//! - Returned position IDs are >= 1.
//!
//! Run:
//! ```bash
//! cargo +nightly fuzz run fuzz_looping_open_position -- -max_total_time=60
//! ```

#![no_main]

use libfuzzer_sys::fuzz_target;
use soroban_sdk::{testutils::Address as _, Address, Env, IntoVal, Symbol};
use looping::LoopingContract;

fuzz_target!(|data: &[u8]| {
    if data.len() < 12 {
        return;
    }
    let collateral = i64::from_le_bytes(data[..8].try_into().unwrap()) as i128;
    let leverage = u32::from_le_bytes(data[8..12].try_into().unwrap());

    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register(LoopingContract, ());
    let user = Address::generate(&env);

    let result = env.try_invoke_contract::<u64, _>(
        &contract_id,
        &Symbol::new(&env, "open_position"),
        soroban_sdk::vec![
            &env,
            user.to_val(),
            collateral.into_val(&env),
            leverage.into_val(&env),
        ],
    );

    if collateral > 0 && (100..=500).contains(&leverage) {
        let position_id = result.expect("open_position with valid args returned error");
        assert!(position_id >= 1, "position_id must be >= 1, got {position_id}");
    }
    // Invalid inputs may error; no further assertion needed.
});
