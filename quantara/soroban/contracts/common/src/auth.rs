//! Standard `require_auth` composition helpers.
//!
//! See common/src/auth.rs in the main codebase for full documentation.

#![allow(dead_code)]

use soroban_sdk::{Address, Env, IntoVal, Symbol, Val, Vec};

/// Require that `caller` has authorised `operation` with the provided `args`.
pub fn assert_caller_auth<T>(env: &Env, caller: &Address, operation: Symbol, args: &T)
where
    T: IntoVal<Env, Vec<Val>>,
{
    caller.require_auth_for_args(args.into_val(env));
    let _ = operation;
}

/// Require auth from every `(Address, args)` pair.
pub fn for_each_auth(env: &Env, principals: &[(Address, Vec<Val>)]) {
    for (addr, args) in principals {
        addr.require_auth_for_args(args.clone());
    }
    let _ = env;
}
