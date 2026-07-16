#![no_std]
use soroban_sdk::{contract, contractimpl, Env, Address};

#[contract]
pub struct VaultContract;

#[contractimpl]
impl VaultContract {
    pub fn deposit(_env: Env, user: Address, _token: Address, amount: i128) -> i128 {
        user.require_auth();
        // Stub for deposit
        amount
    }
}

mod test;
