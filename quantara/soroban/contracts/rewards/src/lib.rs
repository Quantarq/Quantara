//! Rewards contract - reward distribution for the Quantara protocol.
//!
//! Accumulates protocol fees and distributes them to liquidity providers
//! proportionally to their share of the vault.

#![no_std]

use soroban_sdk::{contract, contractimpl, Address, Env};

/// Quantara rewards contract.
#[contract]
pub struct RewardsContract;

#[contractimpl]
impl RewardsContract {
    /// Accrue rewards for a user based on their position size.
    ///
    /// # Arguments
    /// * `env`     - The Soroban environment.
    /// * `user`    - The wallet address to accrue rewards for.
    /// * `accrual` - The reward amount to add (in base units, must be >= 0).
    pub fn accrue(env: Env, user: Address, accrual: i128) {
        assert!(accrual >= 0, "accrual must be non-negative");

        let pending: i128 = env.storage().persistent().get(&user).unwrap_or(0i128);
        env.storage().persistent().set(&user, &(pending + accrual));
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

    struct Fixture {
        env: Env,
        contract_id: Address,
        user: Address,
    }

    fn setup() -> Fixture {
        let env = Env::default();
        env.mock_all_auths();

        let user = Address::generate(&env);
        let contract_id = env.register(RewardsContract, ());

        Fixture {
            env,
            contract_id,
            user,
        }
    }

    #[test]
    fn test_accrue_adds_to_pending_balance() {
        let fx = setup();
        let client = RewardsContractClient::new(&fx.env, &fx.contract_id);

        client.accrue(&fx.user, &100);
        assert_eq!(client.pending_rewards(&fx.user), 100);
    }

    #[test]
    fn test_accrue_rejects_negative_accrual() {
        let fx = setup();
        let client = RewardsContractClient::new(&fx.env, &fx.contract_id);

        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.accrue(&fx.user, &-1);
        }));
        assert!(result.is_err());
        assert_eq!(client.pending_rewards(&fx.user), 0);
    }

    #[test]
    fn test_claim_returns_pending_and_resets_to_zero() {
        let fx = setup();
        let client = RewardsContractClient::new(&fx.env, &fx.contract_id);

        client.accrue(&fx.user, &100);
        let claimed = client.claim(&fx.user);

        assert_eq!(claimed, 100);
        assert_eq!(client.pending_rewards(&fx.user), 0);
    }

    #[test]
    fn test_claim_on_zero_balance_returns_zero() {
        let fx = setup();
        let client = RewardsContractClient::new(&fx.env, &fx.contract_id);

        let claimed = client.claim(&fx.user);
        assert_eq!(claimed, 0);
    }

    #[test]
    fn test_pending_rewards_query_without_claiming() {
        let fx = setup();
        let client = RewardsContractClient::new(&fx.env, &fx.contract_id);

        client.accrue(&fx.user, &500);
        let pending = client.pending_rewards(&fx.user);

        assert_eq!(pending, 500);
        // Pending must still be available after query.
        assert_eq!(client.pending_rewards(&fx.user), 500);
    }

    #[test]
    fn test_multiple_accrue_then_claim() {
        let fx = setup();
        let client = RewardsContractClient::new(&fx.env, &fx.contract_id);

        client.accrue(&fx.user, &100);
        client.accrue(&fx.user, &200);
        client.accrue(&fx.user, &50);

        assert_eq!(client.pending_rewards(&fx.user), 350);
        assert_eq!(client.claim(&fx.user), 350);
        assert_eq!(client.pending_rewards(&fx.user), 0);
    }
}
