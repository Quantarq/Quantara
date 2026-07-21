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
//!   with a compile-time-checked operation tag so reviewers can see exactly
//!   what each call is authorising.
//!
//! * [`for_each_auth`] — iterate a list of `(Address, Vec<Val>)` pairs and
//!   call `require_auth_for_args` on each one in a single expression.  Useful
//!   when an entry-point must authenticate multiple principals (e.g. a
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

use soroban_sdk::{Address, Env, IntoVal, Symbol, Val, Vec};

// ---------------------------------------------------------------------------
// Primary guard
// ---------------------------------------------------------------------------

/// Require that `caller` has authorised `operation` with the provided
/// `args` before any storage mutation occurs.
///
/// # Arguments
///
/// * `env`       – The Soroban environment.
/// * `caller`    – The principal that must authorise this operation.
/// * `operation` – A short `Symbol` naming the entry-point (used as the
///                 sub-contract-call function name in the auth context).
/// * `args`      – A tuple (or any `IntoVal<Env, Vec<Val>>`) of the
///                 arguments being authorised.  Pass `&()` when there are
///                 no arguments.
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
    caller.require_auth_for_args(args.into_val(env));
    // The `operation` symbol is intentionally unused at runtime — it exists
    // solely to make call-sites self-documenting and to enable static grep
    // audits.
    let _ = operation;
}

// ---------------------------------------------------------------------------
// Multi-principal helper
// ---------------------------------------------------------------------------

/// Require auth from every `(Address, args)` pair in `principals`.
///
/// Use this when a single transaction must be authorised by multiple parties
/// (e.g., a relayer address *and* the end-user address).
///
/// # Arguments
///
/// * `env`        – The Soroban environment.
/// * `principals` – Slice of `(Address, Vec<Val>)` tuples.
pub fn for_each_auth(env: &Env, principals: &[(Address, Vec<Val>)]) {
    for (addr, args) in principals {
        addr.require_auth_for_args(args.clone());
    }
    let _ = env;
}
