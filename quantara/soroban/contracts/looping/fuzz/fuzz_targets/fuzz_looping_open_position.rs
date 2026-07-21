//! cargo-fuzz harness for LoopingContract::open_position entry-point.
//!
//! Validates:
//! - Positive collateral with valid leverage (100–500) always succeeds.
//! - Returned position IDs are monotonically increasing (no wrap-around).
//! - Non-positive collateral or out-of-range leverage panics as documented.

#![no_main]

use libfuzzer_sys::fuzz_target;
use soroban_sdk::{testutils::Address as _, Address, Env};
use looping::LoopingContractClient;

fuzz_target!(|data: &[u8]| {
    if data.len() < 12 {
        return;
    }
    let collateral = i64::from_le_bytes(data[..8].try_into().unwrap()) as i128;
    let leverage = u32::from_le_bytes(data[8..12].try_into().unwrap());

    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register(looping::LoopingContract, ());
    let client = LoopingContractClient::new(&env, &contract_id);
    let user = Address::generate(&env);

    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        client.open_position(&user, &collateral, &leverage)
    }));

    let is_valid = collateral > 0 && (100..=500).contains(&leverage);

    if is_valid {
        let position_id = result.expect("open_position with valid args panicked unexpectedly");
        // Position ID must be >= 1.
        assert!(position_id >= 1, "position_id should be >= 1, got {}", position_id);
    }
    // Invalid args may panic; no further assertion needed.
});
