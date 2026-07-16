#![no_std]
use soroban_sdk::{contract, contractimpl, Env, Address};

#[contract]
pub struct RewardsContract;

#[contractimpl]
impl RewardsContract {
    pub fn claim(_env: Env, user: Address) -> i128 {
        user.require_auth();
        // Stub for claim
        100
    }
}

mod test;
