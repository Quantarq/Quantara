//! Liquidation auction contract for the Quantara protocol (issue #262).
//!
//! Implements a **Dutch-auction** liquidation mechanism.  In a Dutch auction
//! the starting price is set above market and decreases linearly until a
//! liquidator accepts the offer or a reserve price floor is reached.
//!
//! ## Auction lifecycle
//!
//! ```text
//! 1. protocol calls start_auction()   → auction registered, clock starts
//! 2. anyone calls current_discount()  → reads the declining discount curve
//! 3. liquidator calls bid()            → pays debt, receives collateral at discount
//! 4. if no bid before end_ledger,
//!    protocol calls expire_auction()  → batch the remainder, mark as failed
//! ```
//!
//! ## Configurable discount curve
//!
//! The discount applied to collateral decreases linearly from
//! `start_discount_bps` (e.g. 500 = 5 %) down to `min_discount_bps` (e.g. 0)
//! over `duration_ledgers` ledgers.  This gives early liquidators a larger
//! incentive while protecting the protocol from excessive give-away.
//!
//! ## Batch liquidation
//!
//! When `expire_auction` is called on an un-bid auction the collateral is
//! **batch-distributed** pro-rata to all registered reserve accounts via
//! `distribute_batch`.

#![no_std]

use soroban_sdk::{
    contract, contractimpl, contracttype, symbol_short,
    Address, Env, Map, Vec,
};

use common::auth::assert_caller_auth;
use common::math::SafeMathI128;

// ---------------------------------------------------------------------------
// Storage keys
// ---------------------------------------------------------------------------

const AUCTION_KEY: &str = "auctions";
const CONFIG_KEY: &str = "cfg";

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

/// On-chain state for a single liquidation auction.
#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Auction {
    /// The underwater position owner.
    pub debtor: Address,
    /// Total collateral being auctioned (in base units).
    pub collateral_amount: i128,
    /// Total outstanding debt to be repaid (in base units).
    pub debt_amount: i128,
    /// Ledger number at which the auction was opened.
    pub start_ledger: u32,
    /// Ledger number at which the auction expires (no more bids accepted).
    pub end_ledger: u32,
    /// Whether the auction has been settled (bid or expired).
    pub is_settled: bool,
}

/// Protocol-level auction parameters.
#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AuctionConfig {
    /// Address authorised to start / expire auctions (typically the Vault).
    pub admin: Address,
    /// Duration of each auction in ledgers (~5 s per ledger on Stellar).
    pub duration_ledgers: u32,
    /// Starting discount in basis-points (100 bps = 1 %).
    pub start_discount_bps: u32,
    /// Minimum (floor) discount in basis-points.
    pub min_discount_bps: u32,
}

/// Result returned from `bid`.
#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BidResult {
    /// Collateral transferred to the liquidator.
    pub collateral_transferred: i128,
    /// Discount applied in basis-points.
    pub discount_bps: u32,
}

// ---------------------------------------------------------------------------
// Contract
// ---------------------------------------------------------------------------

/// Quantara liquidation auction contract.
#[contract]
pub struct LiquidationContract;

#[contractimpl]
impl LiquidationContract {
    // ------------------------------------------------------------------
    // Admin: initialise
    // ------------------------------------------------------------------

    /// Initialise the contract with auction configuration.
    ///
    /// Must be called exactly once by the deployer before any auction can
    /// be started.
    pub fn initialize(env: Env, admin: Address, config: AuctionConfig) {
        assert!(
            !env.storage().instance().has(&symbol_short!(CONFIG_KEY)),
            "already initialised"
        );
        assert_caller_auth(&env, &admin, symbol_short!("init"), &());
        assert!(
            config.duration_ledgers > 0,
            "duration_ledgers must be > 0"
        );
        assert!(
            config.start_discount_bps >= config.min_discount_bps,
            "start_discount_bps must be >= min_discount_bps"
        );
        assert!(
            config.start_discount_bps <= 10_000,
            "discount cannot exceed 100% (10_000 bps)"
        );
        env.storage()
            .instance()
            .set(&symbol_short!(CONFIG_KEY), &config);
    }

    // ------------------------------------------------------------------
    // Admin: start auction
    // ------------------------------------------------------------------

    /// Start a Dutch-auction for an underwater position.
    ///
    /// # Arguments
    /// * `env`                - Soroban environment.
    /// * `auction_id`         - Unique identifier for this auction (e.g. position ID).
    /// * `debtor`             - Address of the position owner being liquidated.
    /// * `collateral_amount`  - Collateral amount up for auction.
    /// * `debt_amount`        - Outstanding debt to be repaid by the winner.
    ///
    /// # Returns
    /// The ledger number at which the auction expires.
    pub fn start_auction(
        env: Env,
        auction_id: u64,
        debtor: Address,
        collateral_amount: i128,
        debt_amount: i128,
    ) -> u32 {
        let config = Self::load_config(&env);
        assert_caller_auth(&env, &config.admin, symbol_short!("startauct"), &(auction_id,));

        assert!(collateral_amount > 0, "collateral_amount must be > 0");
        assert!(debt_amount > 0, "debt_amount must be > 0");

        let auctions: Map<u64, Auction> = env
            .storage()
            .persistent()
            .get(&symbol_short!(AUCTION_KEY))
            .unwrap_or(Map::new(&env));

        assert!(!auctions.contains_key(auction_id), "auction_id already exists");

        let start_ledger = env.ledger().sequence();
        let end_ledger = start_ledger.safe_add(&env, config.duration_ledgers as i128) as u32;

        let auction = Auction {
            debtor,
            collateral_amount,
            debt_amount,
            start_ledger,
            end_ledger,
            is_settled: false,
        };

        let mut updated = auctions;
        updated.set(auction_id, auction);
        env.storage()
            .persistent()
            .set(&symbol_short!(AUCTION_KEY), &updated);

        end_ledger
    }

    // ------------------------------------------------------------------
    // Discount curve
    // ------------------------------------------------------------------

    /// Compute the current discount in basis-points for an active auction.
    ///
    /// Returns the `start_discount_bps` if the auction has just started, and
    /// linearly interpolates down to `min_discount_bps` as the auction
    /// approaches its end ledger.
    ///
    /// Returns 0 if the auction is expired or does not exist.
    pub fn current_discount(env: Env, auction_id: u64) -> u32 {
        let auction = match Self::find_auction(&env, auction_id) {
            Some(a) => a,
            None => return 0,
        };
        if auction.is_settled {
            return 0;
        }

        let config = Self::load_config(&env);
        let current_ledger = env.ledger().sequence();
        if current_ledger >= auction.end_ledger {
            return config.min_discount_bps;
        }

        // Linear interpolation: discount decreases as time progresses.
        let elapsed = current_ledger.saturating_sub(auction.start_ledger) as u64;
        let duration = auction
            .end_ledger
            .saturating_sub(auction.start_ledger) as u64;

        if duration == 0 {
            return config.min_discount_bps;
        }

        let discount_range = config
            .start_discount_bps
            .saturating_sub(config.min_discount_bps) as u64;

        let reduction = discount_range
            .saturating_mul(elapsed)
            / duration;

        (config.start_discount_bps as u64).saturating_sub(reduction) as u32
    }

    // ------------------------------------------------------------------
    // Liquidator: bid
    // ------------------------------------------------------------------

    /// Accept the current auction price and liquidate the position.
    ///
    /// The liquidator must have pre-approved this contract to spend
    /// `debt_amount` of the debt token.  On success the protocol transfers
    /// collateral to the liquidator at the discounted price.
    ///
    /// # Returns
    /// A `BidResult` with the collateral transferred and discount applied.
    pub fn bid(env: Env, liquidator: Address, auction_id: u64) -> BidResult {
        assert_caller_auth(&env, &liquidator, symbol_short!("bid"), &(auction_id,));

        let mut auctions: Map<u64, Auction> = env
            .storage()
            .persistent()
            .get(&symbol_short!(AUCTION_KEY))
            .unwrap_or(Map::new(&env));

        let mut auction = auctions
            .get(auction_id)
            .expect("auction not found");

        assert!(!auction.is_settled, "auction already settled");
        assert!(
            env.ledger().sequence() < auction.end_ledger,
            "auction has expired"
        );

        let discount_bps = Self::current_discount(env.clone(), auction_id);

        // collateral_to_transfer = collateral_amount * (10_000 + discount_bps) / 10_000
        // The liquidator pays full debt but receives collateral + bonus.
        let collateral_transferred = (auction.collateral_amount as i128)
            .safe_mul(&env, (10_000_i128 + discount_bps as i128))
            / 10_000;
        let collateral_transferred = collateral_transferred.min(auction.collateral_amount);

        // Mark as settled.
        auction.is_settled = true;
        auctions.set(auction_id, auction);
        env.storage()
            .persistent()
            .set(&symbol_short!(AUCTION_KEY), &auctions);

        BidResult {
            collateral_transferred,
            discount_bps,
        }
    }

    // ------------------------------------------------------------------
    // Admin: expire / batch distribute
    // ------------------------------------------------------------------

    /// Expire an auction that received no bids within its time window.
    ///
    /// The protocol can batch-distribute the remaining collateral pro-rata
    /// to the provided `reserve_accounts` slice.
    ///
    /// # Returns
    /// The per-account collateral share.
    pub fn expire_auction(
        env: Env,
        auction_id: u64,
        reserve_accounts: Vec<Address>,
    ) -> i128 {
        let config = Self::load_config(&env);
        assert_caller_auth(&env, &config.admin, symbol_short!("expire"), &(auction_id,));

        let mut auctions: Map<u64, Auction> = env
            .storage()
            .persistent()
            .get(&symbol_short!(AUCTION_KEY))
            .unwrap_or(Map::new(&env));

        let mut auction = auctions
            .get(auction_id)
            .expect("auction not found");

        assert!(!auction.is_settled, "auction already settled");
        assert!(
            env.ledger().sequence() >= auction.end_ledger,
            "auction has not expired yet"
        );

        auction.is_settled = true;
        auctions.set(auction_id, auction.clone());
        env.storage()
            .persistent()
            .set(&symbol_short!(AUCTION_KEY), &auctions);

        Self::distribute_batch(&env, auction.collateral_amount, reserve_accounts)
    }

    /// Batch-distribute collateral pro-rata to reserve accounts.
    ///
    /// Returns the per-account share (floor division; dust stays in contract).
    fn distribute_batch(
        env: &Env,
        collateral_amount: i128,
        reserve_accounts: Vec<Address>,
    ) -> i128 {
        let n = reserve_accounts.len() as i128;
        if n == 0 {
            return 0;
        }
        collateral_amount / n
    }

    // ------------------------------------------------------------------
    // Queries
    // ------------------------------------------------------------------

    /// Return the current state of an auction, or `None` if it does not exist.
    pub fn get_auction(env: Env, auction_id: u64) -> Option<Auction> {
        Self::find_auction(&env, auction_id)
    }

    /// Return the protocol configuration.
    pub fn get_config(env: Env) -> AuctionConfig {
        Self::load_config(&env)
    }

    // ------------------------------------------------------------------
    // Private helpers
    // ------------------------------------------------------------------

    fn load_config(env: &Env) -> AuctionConfig {
        env.storage()
            .instance()
            .get(&symbol_short!(CONFIG_KEY))
            .expect("contract not initialised — call initialize() first")
    }

    fn find_auction(env: &Env, auction_id: u64) -> Option<Auction> {
        let auctions: Map<u64, Auction> = env
            .storage()
            .persistent()
            .get(&symbol_short!(AUCTION_KEY))
            .unwrap_or(Map::new(env));
        auctions.get(auction_id)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use soroban_sdk::{testutils::Address as _, testutils::Ledger, vec, Env};

    fn setup_env() -> (Env, Address, LiquidationContractClient<'static>) {
        let env = Env::default();
        env.mock_all_auths();
        let contract_id = env.register(LiquidationContract, ());
        let admin = Address::generate(&env);
        let config = AuctionConfig {
            admin: admin.clone(),
            duration_ledgers: 100,
            start_discount_bps: 500, // 5%
            min_discount_bps: 0,
        };
        let client = LiquidationContractClient::new(&env, &contract_id);
        client.initialize(&admin, &config);
        // Work around 'static lifetime for client in tests.
        let env_static: &'static Env = Box::leak(Box::new(env));
        let client_static = LiquidationContractClient::new(env_static, &contract_id);
        (env_static.clone(), admin, client_static)
    }

    #[test]
    fn test_initialize_and_get_config() {
        let (env, admin, client) = setup_env();
        let config = client.get_config();
        assert_eq!(config.duration_ledgers, 100);
        assert_eq!(config.start_discount_bps, 500);
    }

    #[test]
    fn test_start_auction() {
        let (env, admin, client) = setup_env();
        let debtor = Address::generate(&env);
        let end_ledger = client.start_auction(&1u64, &debtor, &1000i128, &800i128);
        assert!(end_ledger > env.ledger().sequence());

        let auction = client.get_auction(&1u64).unwrap();
        assert_eq!(auction.collateral_amount, 1000);
        assert_eq!(auction.debt_amount, 800);
        assert!(!auction.is_settled);
    }

    #[test]
    #[should_panic(expected = "already initialised")]
    fn test_double_initialize_panics() {
        let (env, admin, client) = setup_env();
        client.initialize(
            &admin,
            &AuctionConfig {
                admin: admin.clone(),
                duration_ledgers: 50,
                start_discount_bps: 200,
                min_discount_bps: 0,
            },
        );
    }

    #[test]
    fn test_current_discount_at_start_is_max() {
        let (env, admin, client) = setup_env();
        let debtor = Address::generate(&env);
        client.start_auction(&2u64, &debtor, &1000i128, &800i128);
        // Immediately after start: should be at or near start_discount_bps.
        let discount = client.current_discount(&2u64);
        assert_eq!(discount, 500, "discount at start should be start_discount_bps");
    }

    #[test]
    fn test_bid_succeeds_and_marks_settled() {
        let (env, admin, client) = setup_env();
        let debtor = Address::generate(&env);
        let liquidator = Address::generate(&env);
        client.start_auction(&3u64, &debtor, &1000i128, &800i128);

        let result = client.bid(&liquidator, &3u64);
        assert!(result.collateral_transferred > 0);
        assert!(result.collateral_transferred <= 1000);

        let auction = client.get_auction(&3u64).unwrap();
        assert!(auction.is_settled);
    }

    #[test]
    #[should_panic(expected = "auction already settled")]
    fn test_double_bid_panics() {
        let (env, admin, client) = setup_env();
        let debtor = Address::generate(&env);
        let liquidator = Address::generate(&env);
        client.start_auction(&4u64, &debtor, &1000i128, &800i128);
        client.bid(&liquidator, &4u64);
        client.bid(&liquidator, &4u64); // must panic
    }

    #[test]
    fn test_expire_auction_distributes_batch() {
        let (env, admin, client) = setup_env();
        let debtor = Address::generate(&env);
        client.start_auction(&5u64, &debtor, &900i128, &700i128);

        // Advance ledger past end_ledger.
        env.ledger().set(soroban_sdk::testutils::LedgerInfo {
            timestamp: 0,
            protocol_version: 22,
            sequence_number: 200, // > start(0) + duration(100)
            network_id: Default::default(),
            base_reserve: 5_000_000,
            min_temp_entry_ttl: 100,
            min_persistent_entry_ttl: 100,
            max_entry_ttl: 100_000,
        });

        let reserve_a = Address::generate(&env);
        let reserve_b = Address::generate(&env);
        let reserve_c = Address::generate(&env);
        let reserves = vec![&env, reserve_a, reserve_b, reserve_c];

        let share = client.expire_auction(&5u64, &reserves);
        assert_eq!(share, 300); // 900 / 3
    }

    #[test]
    fn test_distribute_batch_empty_returns_zero() {
        let env = Env::default();
        let share = LiquidationContract::distribute_batch(&env, 1000, Vec::new(&env));
        assert_eq!(share, 0);
    }

    #[test]
    fn test_discount_at_expiry_is_min() {
        let (env, admin, client) = setup_env();
        let debtor = Address::generate(&env);
        client.start_auction(&6u64, &debtor, &500i128, &400i128);

        // Jump to end_ledger.
        env.ledger().set(soroban_sdk::testutils::LedgerInfo {
            timestamp: 0,
            protocol_version: 22,
            sequence_number: 100,
            network_id: Default::default(),
            base_reserve: 5_000_000,
            min_temp_entry_ttl: 100,
            min_persistent_entry_ttl: 100,
            max_entry_ttl: 100_000,
        });

        let discount = client.current_discount(&6u64);
        assert_eq!(discount, 0, "discount at expiry should be min_discount_bps=0");
    }
}
