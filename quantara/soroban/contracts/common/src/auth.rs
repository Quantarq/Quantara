//! Standard `require_auth` composition helpers (issue #243).
//!
//! Every state-changing entry-point in the Quantara protocol must require the
//! caller to authenticate against the operation before mutating any storage.
//! Forgetting a single `require_auth()` call is a critical vulnerability.
//!
//! This module provides two ergonomic helpers:
//!
//! * [`assert_caller_auth`] — the primary guard.  Call it at the top of every
//!   state-mutating entry-point.  It combines `Address::require_auth_for_args`
//!   with an `operation` symbol that is **folded into the authorised args**, so
//!   two entry points with identical numeric arguments still produce distinct
//!   signature payloads (domain separation / replay protection).
//!
//! * [`for_each_auth`] — iterate a list of `(Address, Symbol, Vec<Val>)` triples
//!   and require each principal's auth for its own operation in a single pass.
//!   Useful when an entry-point must authenticate multiple principals (e.g. a
//!   relayer and a user simultaneously).
//!
//! # Usage
//!
//! ```ignore
//! use common::auth::{assert_caller_auth, for_each_auth};
//! use soroban_sdk::{symbol_short, vec, Address, Env};
//!
//! pub fn deposit(env: Env, user: Address, amount: i128) {
//!     assert_caller_auth(&env, &user, symbol_short!("deposit"), &(amount,));
//!     // ... state mutations ...
//! }
//! ```

#![allow(dead_code)]

use soroban_sdk::{vec, Address, Env, IntoVal, Symbol, Val, Vec};

// ---------------------------------------------------------------------------
// Primary guard
// ---------------------------------------------------------------------------

/// Require that `caller` has authorised `operation` with the provided
/// `args` before any storage mutation occurs.
///
/// The `operation` symbol is prepended to `args` and passed to
/// `require_auth_for_args`, so the signed payload is domain-separated by entry
/// point: `deposit(100)` and `withdraw(100)` authorise different byte payloads
/// even though their numeric arguments are identical.
///
/// # Arguments
///
/// * `env`       – The Soroban environment.
/// * `caller`    – The principal that must authorise this operation.
/// * `operation` – A short `Symbol` naming the entry-point.  It is folded into
///   the authorised args as the leading element.
/// * `args`      – A tuple (or any `IntoVal<Env, Vec<Val>>`) of the
///   arguments being authorised.  Pass `&()` when there are no arguments.
///
/// # Panics
///
/// Panics (via the Soroban host's auth machinery) if `caller` has not
/// provided a valid signature for `operation(args…)`.
///
/// # Example
///
/// ```ignore
/// assert_caller_auth(&env, &user, symbol_short!("withdraw"), &(amount,));
/// ```
pub fn assert_caller_auth<T>(env: &Env, caller: &Address, operation: Symbol, args: &T)
where
    T: IntoVal<Env, Vec<Val>>,
{
    // Prepend the operation symbol so the signed args are domain-separated by
    // entry point. Without this, two operations sharing an argument tuple
    // (e.g. deposit/withdraw of the same amount) would produce identical
    // authorised payloads and signatures would replay across them.
    let mut signed = vec![env, operation.to_val()];
    for v in args.into_val(env) {
        signed.push_back(v);
    }
    caller.require_auth_for_args(signed);
}

// ---------------------------------------------------------------------------
// Multi-principal helper
// ---------------------------------------------------------------------------

/// Require auth from every `(Address, Symbol, Vec<Val>)` triple in `principals`.
///
/// Use this when a single transaction must be authorised by multiple parties
/// (e.g., a relayer address *and* the end-user address). Each principal's
/// `operation` symbol is folded into its args exactly as in
/// [`assert_caller_auth`], so every principal is domain-separated too.
///
/// # Arguments
///
/// * `env`        – The Soroban environment.
/// * `principals` – Slice of `(Address, Symbol, Vec<Val>)` triples.
pub fn for_each_auth(env: &Env, principals: &[(Address, Symbol, Vec<Val>)]) {
    for (addr, operation, args) in principals {
        let mut signed = vec![env, operation.to_val()];
        for v in args.clone() {
            signed.push_back(v);
        }
        addr.require_auth_for_args(signed);
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
    use soroban_sdk::testutils::AuthorizedFunction;
    use soroban_sdk::{contract, contractimpl, symbol_short, Address, Env, Symbol, TryFromVal};

    /// Minimal probe with two entry points that share an argument tuple, so the
    /// only thing distinguishing their auth payloads is the operation symbol.
    #[contract]
    pub struct AuthProbe;

    #[contractimpl]
    impl AuthProbe {
        pub fn deposit(env: Env, user: Address, amount: i128) {
            assert_caller_auth(&env, &user, symbol_short!("deposit"), &(amount,));
        }

        pub fn withdraw(env: Env, user: Address, amount: i128) {
            assert_caller_auth(&env, &user, symbol_short!("withdraw"), &(amount,));
        }
    }

    fn auth_args(env: &Env) -> Vec<Val> {
        let auths = env.auths();
        assert_eq!(auths.len(), 1, "expected exactly one auth tree");
        let (_addr, invocation) = &auths[0];
        match &invocation.function {
            AuthorizedFunction::Contract((_contract, _fn_name, args)) => args.clone(),
            _ => panic!("expected a Contract auth function"),
        }
    }

    #[test]
    fn test_operation_symbol_domain_separates_auth() {
        let env = Env::default();
        env.mock_all_auths();

        let user = Address::generate(&env);
        let contract_id = env.register(AuthProbe, ());
        let client = AuthProbeClient::new(&env, &contract_id);

        client.deposit(&user, &100_i128);
        let deposit_args = auth_args(&env);

        client.withdraw(&user, &100_i128);
        let withdraw_args = auth_args(&env);

        // The operation symbol is folded in as the leading arg, so the payload
        // is `[operation, amount]` rather than `[amount]`.
        assert_eq!(deposit_args.len(), 2);
        assert_eq!(withdraw_args.len(), 2);

        let deposit_op = Symbol::try_from_val(&env, &deposit_args.get(0).unwrap()).unwrap();
        let withdraw_op = Symbol::try_from_val(&env, &withdraw_args.get(0).unwrap()).unwrap();
        assert_eq!(deposit_op, symbol_short!("deposit"));
        assert_eq!(withdraw_op, symbol_short!("withdraw"));

        assert_ne!(
            deposit_args, withdraw_args,
            "deposit(100) and withdraw(100) must produce distinct auth payloads"
        );
    }
}
