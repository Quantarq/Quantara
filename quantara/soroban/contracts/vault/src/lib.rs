//! Vault contract — on-chain collateral ledger for the Quantara protocol.
//!
//! The vault escrows Stellar Asset Contract (SAC) tokens on behalf of users.
//! `deposit` moves the stated asset from the user into this contract and
//! credits the user's per-asset balance; `withdraw` pays the asset back out
//! of the contract and debits the ledger.  Balances are tracked per
//! `(user, asset)` pair, so collateral of different assets can never be
//! mixed or withdrawn against each other.
//!
//! All arithmetic uses the workspace's checked [`SafeMathI128`], so an
//! overflowing deposit/withdraw panics with a structured `MathError` instead
//! of trapping the host.

#![no_std]

use soroban_sdk::{contract, contractimpl, symbol_short, token, Address, Env};

use common::auth::assert_caller_auth;
use common::math::SafeMathI128;

/// Quantara vault contract.
#[contract]
pub struct VaultContract;

#[contractimpl]
impl VaultContract {
    /// Deposit collateral into the vault.
    ///
    /// Transfers `amount` of `asset` from `user` into this contract, then
    /// credits the user's ledger balance.
    ///
    /// # Arguments
    /// * `env`    - The Soroban environment.
    /// * `user`   - The wallet address making the deposit.
    /// * `asset`  - The Stellar Asset Contract token to escrow.
    /// * `amount` - The amount to deposit (in base units, must be > 0).
    pub fn deposit(env: Env, user: Address, asset: Address, amount: i128) {
        assert_caller_auth(
            &env,
            &user,
            symbol_short!("deposit"),
            &(asset.clone(), amount),
        );
        assert!(amount > 0, "deposit amount must be positive");

        // Move the asset into the vault before crediting the ledger so the
        // recorded balance always corresponds to escrowed tokens.
        token::Client::new(&env, &asset).transfer(&user, &env.current_contract_address(), &amount);

        let balance: i128 = env
            .storage()
            .persistent()
            .get(&(user.clone(), asset.clone()))
            .unwrap_or(0i128);
        env.storage()
            .persistent()
            .set(&(user, asset), &balance.safe_add(&env, amount));
    }

    /// Withdraw collateral from the vault.
    ///
    /// Transfers `amount` of `asset` from this contract back to `user`, then
    /// debits the user's ledger balance.
    ///
    /// # Arguments
    /// * `env`    - The Soroban environment.
    /// * `user`   - The wallet address requesting the withdrawal.
    /// * `asset`  - The Stellar Asset Contract token to pay out.
    /// * `amount` - The amount to withdraw (in base units, must be > 0).
    pub fn withdraw(env: Env, user: Address, asset: Address, amount: i128) {
        assert_caller_auth(
            &env,
            &user,
            symbol_short!("withdraw"),
            &(asset.clone(), amount),
        );
        assert!(amount > 0, "withdrawal amount must be positive");

        let balance: i128 = env
            .storage()
            .persistent()
            .get(&(user.clone(), asset.clone()))
            .unwrap_or(0i128);
        assert!(balance >= amount, "insufficient balance");

        // Pay out from the vault before debiting the ledger; a failed
        // transfer reverts the whole invocation, so the two stay atomic.
        token::Client::new(&env, &asset).transfer(&env.current_contract_address(), &user, &amount);
        env.storage()
            .persistent()
            .set(&(user, asset), &balance.safe_sub(&env, amount));
    }

    /// Query the collateral balance of a user for a specific asset.
    pub fn balance(env: Env, user: Address, asset: Address) -> i128 {
        env.storage()
            .persistent()
            .get(&(user, asset))
            .unwrap_or(0i128)
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
    use soroban_sdk::token::{StellarAssetClient, TokenClient};
    use soroban_sdk::{vec, IntoVal};

    struct Fixture {
        env: Env,
        contract_id: Address,
        user: Address,
        asset: Address,
    }

    fn setup() -> Fixture {
        let env = Env::default();
        env.mock_all_auths();

        let admin = Address::generate(&env);
        let user = Address::generate(&env);
        let contract_id = env.register(VaultContract, ());
        let asset = env.register_stellar_asset_contract_v2(admin).address();

        Fixture {
            env,
            contract_id,
            user,
            asset,
        }
    }

    fn mint(fx: &Fixture, to: &Address, amount: i128) {
        StellarAssetClient::new(&fx.env, &fx.asset).mint(to, &amount);
    }

    fn balance_of(fx: &Fixture, address: &Address) -> i128 {
        TokenClient::new(&fx.env, &fx.asset).balance(address)
    }

    fn ledger_balance(fx: &Fixture) -> i128 {
        let client = VaultContractClient::new(&fx.env, &fx.contract_id);
        client.balance(&fx.user, &fx.asset)
    }

    #[test]
    fn test_deposit_transfers_tokens_into_vault() {
        let fx = setup();
        mint(&fx, &fx.user, 1_000);

        let client = VaultContractClient::new(&fx.env, &fx.contract_id);
        client.deposit(&fx.user, &fx.asset, &1_000);

        // The contract now holds the tokens and the ledger matches.
        assert_eq!(balance_of(&fx, &fx.contract_id), 1_000);
        assert_eq!(balance_of(&fx, &fx.user), 0);
        assert_eq!(ledger_balance(&fx), 1_000);
    }

    #[test]
    fn test_deposit_without_funds_panics() {
        let fx = setup();
        // No mint: the user holds nothing, so the transfer must fail.
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let client = VaultContractClient::new(&fx.env, &fx.contract_id);
            client.deposit(&fx.user, &fx.asset, &100);
        }));
        assert!(result.is_err());
        assert_eq!(ledger_balance(&fx), 0);
    }

    #[test]
    fn test_withdraw_round_trip_returns_tokens() {
        let fx = setup();
        mint(&fx, &fx.user, 1_000);
        let client = VaultContractClient::new(&fx.env, &fx.contract_id);
        client.deposit(&fx.user, &fx.asset, &1_000);

        client.withdraw(&fx.user, &fx.asset, &400);

        assert_eq!(balance_of(&fx, &fx.user), 400);
        assert_eq!(balance_of(&fx, &fx.contract_id), 600);
        assert_eq!(ledger_balance(&fx), 600);
    }

    #[test]
    fn test_withdraw_insufficient_balance_panics() {
        let fx = setup();
        mint(&fx, &fx.user, 100);
        let client = VaultContractClient::new(&fx.env, &fx.contract_id);
        client.deposit(&fx.user, &fx.asset, &100);

        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.withdraw(&fx.user, &fx.asset, &101);
        }));
        assert!(result.is_err());

        // Nothing moved and the ledger is unchanged.
        assert_eq!(balance_of(&fx, &fx.contract_id), 100);
        assert_eq!(ledger_balance(&fx), 100);
    }

    #[test]
    fn test_balances_are_isolated_per_asset() {
        let fx = setup();
        mint(&fx, &fx.user, 1_000);

        // A second, distinct asset for the same user.
        let admin = Address::generate(&fx.env);
        let other_asset = fx.env.register_stellar_asset_contract_v2(admin).address();
        StellarAssetClient::new(&fx.env, &other_asset).mint(&fx.user, &500);

        let client = VaultContractClient::new(&fx.env, &fx.contract_id);
        client.deposit(&fx.user, &fx.asset, &1_000);
        client.deposit(&fx.user, &other_asset, &500);

        assert_eq!(client.balance(&fx.user, &fx.asset), 1_000);
        assert_eq!(client.balance(&fx.user, &other_asset), 500);

        // Overdrawing one asset must never dip into the other asset's ledger.
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.withdraw(&fx.user, &other_asset, &600); // only 500 deposited in other_asset
        }));
        assert!(result.is_err());
        assert_eq!(client.balance(&fx.user, &fx.asset), 1_000);
        assert_eq!(client.balance(&fx.user, &other_asset), 500);
    }

    #[test]
    fn test_ledger_never_overflows_or_wraps() {
        let fx = setup();
        mint(&fx, &fx.user, i128::MAX);

        let client = VaultContractClient::new(&fx.env, &fx.contract_id);
        client.deposit(&fx.user, &fx.asset, &i128::MAX);
        assert_eq!(ledger_balance(&fx), i128::MAX);

        // The ledger is escrow-bounded: a further deposit needs tokens the
        // user no longer holds, so it must fail cleanly and leave the ledger
        // at exactly i128::MAX — never wrapped or corrupted. (The `safe_add`
        // in `deposit` would surface `MathError::Overflow` if the ledger could
        // ever exceed i128::MAX, which real custody makes unreachable.)
        let result = fx.env.try_invoke_contract::<(), soroban_sdk::Error>(
            &fx.contract_id,
            &symbol_short!("deposit"),
            vec![
                &fx.env,
                fx.user.to_val(),
                fx.asset.to_val(),
                (1_i128).into_val(&fx.env),
            ],
        );
        assert!(result.is_err(), "second deposit must be rejected");

        assert_eq!(ledger_balance(&fx), i128::MAX);
        assert_eq!(balance_of(&fx, &fx.contract_id), i128::MAX);
    }
}
