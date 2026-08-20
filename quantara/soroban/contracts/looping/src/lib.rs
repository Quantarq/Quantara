//! Looping contract - leverage loop engine for the Quantara protocol.
//!
//! This contract allows users to create and manage leveraged positions on
//! the Stellar network by automating the borrow->swap->redeposit loop.

#![no_std]

use soroban_sdk::{contract, contractimpl, symbol_short, Address, Env};

use common::auth::assert_caller_auth;

/// Quantara looping contract.
#[contract]
pub struct LoopingContract;

#[contractimpl]
impl LoopingContract {
    /// Open a leveraged position.
    ///
    /// # Arguments
    /// * `env`        - The Soroban environment.
    /// * `user`       - The wallet address opening the position.
    /// * `collateral` - The amount of collateral to deposit (in base units).
    /// * `leverage`   - The desired leverage multiplier (1-5, scaled x100).
    ///
    /// # Returns
    /// The position ID assigned to this new position.
    pub fn open_position(env: Env, user: Address, collateral: i128, leverage: u32) -> u64 {
        assert_caller_auth(
            &env,
            &user,
            symbol_short!("open_pos"),
            &(collateral, leverage),
        );

        assert!(collateral > 0, "collateral must be positive");
        assert!(
            (100..=500).contains(&leverage),
            "leverage must be 1x-5x (100-500)"
        );

        let key = symbol_short!("pos_cnt");
        let count: u64 = env.storage().instance().get(&key).unwrap_or(0u64);
        let position_id = count + 1;
        env.storage().instance().set(&key, &position_id);

        position_id
    }

    /// Close an existing leveraged position.
    ///
    /// # Arguments
    /// * `env`         - The Soroban environment.
    /// * `user`        - The wallet address that owns the position.
    /// * `position_id` - The ID of the position to close.
    pub fn close_position(env: Env, user: Address, position_id: u64) {
        assert_caller_auth(&env, &user, symbol_short!("close_pos"), &(position_id,));
        // Stub: full unwind logic will be implemented in a future PR.
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    extern crate std;

    use super::*;
    use soroban_sdk::testutils::Address as _;

    struct Fixture {
        env: Env,
        contract_id: Address,
        user: Address,
    }

    fn setup() -> Fixture {
        let env = Env::default();
        env.mock_all_auths();

        let user = Address::generate(&env);
        let contract_id = env.register(LoopingContract, ());

        Fixture {
            env,
            contract_id,
            user,
        }
    }

    #[test]
    fn test_open_position_returns_first_id() {
        let fx = setup();
        let client = LoopingContractClient::new(&fx.env, &fx.contract_id);

        let id = client.open_position(&fx.user, &1_000, &200);
        assert_eq!(id, 1);
    }

    #[test]
    fn test_open_position_returns_incrementing_ids() {
        let fx = setup();
        let client = LoopingContractClient::new(&fx.env, &fx.contract_id);

        assert_eq!(client.open_position(&fx.user, &1_000, &200), 1);
        assert_eq!(client.open_position(&fx.user, &2_000, &300), 2);
        assert_eq!(client.open_position(&fx.user, &500, &100), 3);
    }

    #[test]
    fn test_open_position_rejects_zero_collateral() {
        let fx = setup();
        let client = LoopingContractClient::new(&fx.env, &fx.contract_id);

        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.open_position(&fx.user, &0, &200);
        }));
        assert!(result.is_err());
    }

    #[test]
    fn test_open_position_rejects_negative_collateral() {
        let fx = setup();
        let client = LoopingContractClient::new(&fx.env, &fx.contract_id);

        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.open_position(&fx.user, &-1, &200);
        }));
        assert!(result.is_err());
    }

    #[test]
    fn test_open_position_rejects_leverage_below_100() {
        let fx = setup();
        let client = LoopingContractClient::new(&fx.env, &fx.contract_id);

        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.open_position(&fx.user, &1_000, &99);
        }));
        assert!(result.is_err());
    }

    #[test]
    fn test_open_position_rejects_leverage_above_500() {
        let fx = setup();
        let client = LoopingContractClient::new(&fx.env, &fx.contract_id);

        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.open_position(&fx.user, &1_000, &501);
        }));
        assert!(result.is_err());
    }

    #[test]
    fn test_open_position_accepts_leverage_boundaries() {
        let fx = setup();
        let client = LoopingContractClient::new(&fx.env, &fx.contract_id);

        assert_eq!(client.open_position(&fx.user, &1_000, &100), 1);
        assert_eq!(client.open_position(&fx.user, &1_000, &500), 2);
    }

    #[test]
    fn test_close_position_does_not_panic() {
        let fx = setup();
        let client = LoopingContractClient::new(&fx.env, &fx.contract_id);

        let id = client.open_position(&fx.user, &1_000, &200);
        client.close_position(&fx.user, &id);
    }
}
