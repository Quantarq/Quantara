//! Vault contract – collateral management for the Quantara protocol.
//!
//! Manages user deposits and withdrawals of collateral, enforcing health-ratio
//! constraints before allowing further borrowing.

#![no_std]

use soroban_sdk::{contract, contractimpl, Address, Env, I128};

/// Quantara vault contract.
#[contract]
pub struct VaultContract;

#[contractimpl]
impl VaultContract {
    /// Deposit collateral into the vault.
    ///
    /// # Arguments
    /// * `env`    - The Soroban environment.
    /// * `user`   - The wallet address making the deposit.
    /// * `amount` - The amount to deposit (in base units, must be > 0).
    pub fn deposit(env: Env, user: Address, amount: I128) {
        user.require_auth();
        assert!(amount > 0, "deposit amount must be positive");

        let balance: I128 = env.storage().persistent().get(&user).unwrap_or(0i128);
        env.storage().persistent().set(&user, &(balance + amount));
    }

    /// Withdraw collateral from the vault.
    ///
    /// # Arguments
    /// * `env`    - The Soroban environment.
    /// * `user`   - The wallet address requesting the withdrawal.
    /// * `amount` - The amount to withdraw (in base units, must be > 0).
    pub fn withdraw(env: Env, user: Address, amount: I128) {
        user.require_auth();
        assert!(amount > 0, "withdrawal amount must be positive");

        let balance: I128 = env.storage().persistent().get(&user).unwrap_or(0i128);
        assert!(balance >= amount, "insufficient balance");
        env.storage().persistent().set(&user, &(balance - amount));
    }

    /// Query the collateral balance of a user.
    pub fn balance(env: Env, user: Address) -> I128 {
        env.storage().persistent().get(&user).unwrap_or(0i128)
    }
}
