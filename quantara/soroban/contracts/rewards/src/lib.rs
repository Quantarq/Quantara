//! Rewards contract - reward distribution for the Quantara protocol.
//!
//! Accumulates protocol fees and distributes them to liquidity providers
//! proportionally to their share of the vault.
//!
//! Accrual is a protocol-driven credit and is therefore gated behind a single
//! admin principal persisted by `initialize`; claiming remains user-signed.

#![no_std]

use soroban_sdk::{contract, contractimpl, symbol_short, Address, Env};

use common::auth::assert_caller_auth;
use common::math::SafeMathI128;

/// Quantara rewards contract.
#[contract]
pub struct RewardsContract;

#[contractimpl]
impl RewardsContract {
    /// Initialise the contract with the principal authorised to accrue rewards.
    ///
    /// Must be called exactly once before any accrual is possible.
    ///
    /// # Arguments
    /// * `env`   - The Soroban environment.
    /// * `admin` - The address permitted to call `accrue`.
    pub fn initialize(env: Env, admin: Address) {
        assert!(
            !env.storage().instance().has(&symbol_short!("admin")),
            "already initialised"
        );
        assert_caller_auth(&env, &admin, symbol_short!("init"), &());
        env.storage()
            .instance()
            .set(&symbol_short!("admin"), &admin);
    }

    /// Accrue rewards for a user based on their position size.
    ///
    /// Only the initialised admin may accrue. The accrual is applied with
    /// checked arithmetic so an overflow surfaces a `MathError` instead of a
    /// raw host trap.
    ///
    /// # Arguments
    /// * `env`     - The Soroban environment.
    /// * `user`    - The wallet address to accrue rewards for.
    /// * `accrual` - The reward amount to add (in base units, must be >= 0).
    pub fn accrue(env: Env, user: Address, accrual: i128) {
        let admin: Address = env
            .storage()
            .instance()
            .get(&symbol_short!("admin"))
            .expect("rewards not initialised — call initialize() first");
        assert_caller_auth(
            &env,
            &admin,
            symbol_short!("accrue"),
            &(user.clone(), accrual),
        );

        assert!(accrual >= 0, "accrual must be non-negative");

        let pending: i128 = env.storage().persistent().get(&user).unwrap_or(0i128);
        env.storage()
            .persistent()
            .set(&user, &pending.safe_add(&env, accrual));
    }

    /// Claim all pending rewards for a user.
    ///
    /// # Arguments
    /// * `env`  - The Soroban environment.
    /// * `user` - The wallet address claiming rewards.
    ///
    /// # Returns
    /// The total amount of rewards claimed.
    pub fn claim(env: Env, user: Address) -> i128 {
        user.require_auth();

        let pending: i128 = env.storage().persistent().get(&user).unwrap_or(0i128);

        // Reset pending balance and return claimed amount.
        env.storage().persistent().set(&user, &0i128);
        pending
    }

    /// Query pending rewards for a user without claiming.
    pub fn pending_rewards(env: Env, user: Address) -> i128 {
        env.storage().persistent().get(&user).unwrap_or(0i128)
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
    use soroban_sdk::testutils::{MockAuth, MockAuthInvoke};
    use soroban_sdk::vec;

    #[test]
    fn test_admin_accrue_and_claim() {
        let env = Env::default();
        env.mock_all_auths();

        let admin = Address::generate(&env);
        let user = Address::generate(&env);
        let contract_id = env.register(RewardsContract, ());
        let client = RewardsContractClient::new(&env, &contract_id);

        client.initialize(&admin);
        client.accrue(&user, &100_i128);
        assert_eq!(client.pending_rewards(&user), 100);

        let claimed = client.claim(&user);
        assert_eq!(claimed, 100);
        assert_eq!(client.pending_rewards(&user), 0);
    }

    #[test]
    #[should_panic(expected = "already initialised")]
    fn test_initialize_rejects_second_call() {
        let env = Env::default();
        env.mock_all_auths();

        let admin = Address::generate(&env);
        let contract_id = env.register(RewardsContract, ());
        let client = RewardsContractClient::new(&env, &contract_id);

        client.initialize(&admin);
        client.initialize(&admin);
    }

    #[test]
    fn test_non_admin_cannot_accrue() {
        let env = Env::default();
        let contract_id = env.register(RewardsContract, ());
        let admin = Address::generate(&env);
        let user = Address::generate(&env);

        // Authorise only the admin's `initialize` call; nothing authorises the
        // subsequent `accrue`.
        let init = MockAuthInvoke {
            contract: &contract_id,
            fn_name: "initialize",
            args: vec![&env],
            sub_invokes: &[],
        };
        env.mock_auths(&[MockAuth {
            address: &admin,
            invoke: &init,
        }]);

        let client = RewardsContractClient::new(&env, &contract_id);
        client.initialize(&admin);

        // `accrue` requires the admin's authorisation, which was only mocked
        // for `initialize` — so this call fails no matter who invokes it.
        let res = client.try_accrue(&user, &100_i128);
        assert!(res.is_err(), "non-admin accrual must be rejected");
        assert_eq!(client.pending_rewards(&user), 0);
    }

    #[test]
    fn test_accrue_overflow_returns_error() {
        let env = Env::default();
        env.mock_all_auths();

        let admin = Address::generate(&env);
        let user = Address::generate(&env);
        let contract_id = env.register(RewardsContract, ());
        let client = RewardsContractClient::new(&env, &contract_id);

        client.initialize(&admin);
        client.accrue(&user, &i128::MAX);

        // Adding 1 to i128::MAX must surface a contract error (MathError::Overflow)
        // rather than silently wrapping.
        let res = client.try_accrue(&user, &1_i128);
        assert!(res.is_err(), "overflow must surface an error");
    }

    #[test]
    fn test_claim_on_zero_balance_returns_zero() {
        let env = Env::default();
        env.mock_all_auths();

        let admin = Address::generate(&env);
        let user = Address::generate(&env);
        let contract_id = env.register(RewardsContract, ());
        let client = RewardsContractClient::new(&env, &contract_id);

        client.initialize(&admin);

        let claimed = client.claim(&user);
        assert_eq!(claimed, 0);
    }

    #[test]
    fn test_pending_rewards_query_without_claiming() {
        let env = Env::default();
        env.mock_all_auths();

        let admin = Address::generate(&env);
        let user = Address::generate(&env);
        let contract_id = env.register(RewardsContract, ());
        let client = RewardsContractClient::new(&env, &contract_id);

        client.initialize(&admin);
        client.accrue(&user, &500_i128);
        let pending = client.pending_rewards(&user);

        assert_eq!(pending, 500);
        assert_eq!(client.pending_rewards(&user), 500);
    }

    #[test]
    fn test_multiple_accrue_then_claim() {
        let env = Env::default();
        env.mock_all_auths();

        let admin = Address::generate(&env);
        let user = Address::generate(&env);
        let contract_id = env.register(RewardsContract, ());
        let client = RewardsContractClient::new(&env, &contract_id);

        client.initialize(&admin);
        client.accrue(&user, &100_i128);
        client.accrue(&user, &200_i128);
        client.accrue(&user, &50_i128);

        assert_eq!(client.pending_rewards(&user), 350);
        assert_eq!(client.claim(&user), 350);
        assert_eq!(client.pending_rewards(&user), 0);
    }
}
