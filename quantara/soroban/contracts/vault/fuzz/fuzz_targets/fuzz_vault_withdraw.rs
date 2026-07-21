//! cargo-fuzz harness for VaultContract::withdraw entry-point.

#![no_main]

use libfuzzer_sys::fuzz_target;
use soroban_sdk::{testutils::Address as _, Address, Env};
use vault::VaultContractClient;

fuzz_target!(|data: &[u8]| {
    if data.len() < 16 {
        return;
    }
    let initial_deposit = i64::from_le_bytes(data[..8].try_into().unwrap()).unsigned_abs() as i128;
    let withdraw_amount = i64::from_le_bytes(data[8..16].try_into().unwrap()) as i128;

    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register(vault::VaultContract, ());
    let client = VaultContractClient::new(&env, &contract_id);
    let user = Address::generate(&env);

    // Seed a known balance.
    if initial_deposit > 0 {
        client.deposit(&user, &initial_deposit);
    }

    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        client.withdraw(&user, &withdraw_amount);
    }));

    let current_balance = client.balance(&user);

    if withdraw_amount > 0 && withdraw_amount <= initial_deposit {
        // Must succeed and produce correct balance.
        assert!(
            result.is_ok(),
            "valid withdraw(amount={}, balance={}) panicked",
            withdraw_amount,
            initial_deposit
        );
        assert_eq!(current_balance, initial_deposit - withdraw_amount);
    }
    // Insufficient balance or non-positive amount may panic (documented).
    // We only assert the balance never goes negative.
    assert!(
        current_balance >= 0,
        "balance went negative: {}",
        current_balance
    );
});
