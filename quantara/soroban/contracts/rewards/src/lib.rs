//! Rewards contract – reward distribution for the Quantara protocol.
//!
//! Accumulates protocol fees and distributes them to liquidity providers
//! proportionally to their share of the vault.

#![no_std]

use soroban_sdk::{contract, contractimpl, Address, Env, I128};

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
    pub fn accrue(env: Env, user: Address, accrual: I128) {
        assert!(accrual >= 0, "accrual must be non-negative");

        let pending: I128 = env.storage().persistent().get(&user).unwrap_or(0i128);
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
    pub fn claim(env: Env, user: Address) -> I128 {
        user.require_auth();

        let pending: I128 = env.storage().persistent().get(&user).unwrap_or(0i128);

        // Reset pending balance and return claimed amount.
        env.storage().persistent().set(&user, &0i128);
        pending
    }

    /// Query pending rewards for a user without claiming.
    pub fn pending_rewards(env: Env, user: Address) -> I128 {
        env.storage().persistent().get(&user).unwrap_or(0i128)
    }
}
