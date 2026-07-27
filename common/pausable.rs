#![no_std]

use soroban_sdk::{Address, Env, Symbol};

const PAUSED: Symbol = Symbol::short("paused");
const ADMIN: Symbol = Symbol::short("admin");

pub trait Pausable {
    fn pause(env: Env);
    fn unpause(env: Env);
    fn paused(env: Env) -> bool;
}

pub fn init_admin(env: &Env, admin: &Address) {
    if env.storage().instance().has(&ADMIN) {
        return;
    }

    env.storage().instance().set(&ADMIN, admin);
    env.storage().instance().set(&PAUSED, &false);
}

pub fn pause(env: &Env, caller: &Address) {
    require_admin(env, caller);
    env.storage().instance().set(&PAUSED, &true);
}

pub fn unpause(env: &Env, caller: &Address) {
    require_admin(env, caller);
    env.storage().instance().set(&PAUSED, &false);
}

pub fn paused(env: &Env) -> bool {
    env.storage().instance().get(&PAUSED).unwrap_or(false)
}

pub fn require_not_paused(env: &Env) {
    if paused(env) {
        panic!("Protocol paused");
    }
}

pub fn require_admin(env: &Env, caller: &Address) {
    caller.require_auth();

    let admin: Address = env
        .storage()
        .instance()
        .get(&ADMIN)
        .expect("admin not initialized");

    if admin != *caller {
        panic!("admin required");
    }
}
