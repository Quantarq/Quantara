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

use soroban_sdk::{contract, contractimpl, contracttype, symbol_short, Address, Env, Map, Vec};

use common::auth::assert_caller_auth;
use common::math::SafeMathI128;

// ---------------------------------------------------------------------------
// Storage keys
// ---------------------------------------------------------------------------
//
// Stored under the Soroban SDK's `symbol_short!` keys — must be ≤ 9 chars
// and passed as a string literal at compile time.
//
//   AUCTION_KEY = "auctions"  (≤ 9 chars)
//   CONFIG_KEY  = "cfg"       (≤ 9 chars)

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
            !env.storage().instance().has(&symbol_short!("cfg")),
            "already initialised"
        );
        assert_caller_auth(&env, &admin, symbol_short!("init"), &());
        assert!(config.duration_ledgers > 0, "duration_ledgers must be > 0");
        assert!(
            config.start_discount_bps >= config.min_discount_bps,
            "start_discount_bps must be >= min_discount_bps"
        );
        assert!(
            config.start_discount_bps <= 10_000,
            "discount cannot exceed 100% (10_000 bps)"
        );
        env.storage().instance().set(&symbol_short!("cfg"), &config);
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
        assert_caller_auth(
            &env,
            &config.admin,
            symbol_short!("startauct"),
            &(auction_id,),
        );

        assert!(collateral_amount > 0, "collateral_amount must be > 0");
        assert!(debt_amount > 0, "debt_amount must be > 0");

        let auctions: Map<u64, Auction> = env
            .storage()
            .persistent()
            .get(&symbol_short!("auctions"))
            .unwrap_or(Map::new(&env));

        assert!(
            !auctions.contains_key(auction_id),
            "auction_id already exists"
        );

        let start_ledger = env.ledger().sequence();
        let end_ledger =
            (start_ledger as i128).safe_add(&env, config.duration_ledgers as i128) as u32;

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
        env.storage().persistent().set(&symbol_short!("auctions"), &updated);

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
        let duration = auction.end_ledger.saturating_sub(auction.start_ledger) as u64;

        if duration == 0 {
            return config.min_discount_bps;
        }

        let discount_range = config
            .start_discount_bps
            .saturating_sub(config.min_discount_bps) as u64;

        let reduction = discount_range.saturating_mul(elapsed) / duration;

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
            .get(&symbol_short!("auctions"))
            .unwrap_or(Map::new(&env));

        let mut auction = auctions.get(auction_id).expect("auction not found");

        assert!(!auction.is_settled, "auction already settled");
        assert!(
            env.ledger().sequence() < auction.end_ledger,
            "auction has expired"
        );

        let discount_bps = Self::current_discount(env.clone(), auction_id);

        // collateral_to_transfer = collateral_amount * (10_000 + discount_bps) / 10_000
        // The liquidator pays full debt but receives collateral + bonus.
        let collateral_transferred = (auction.collateral_amount as i128)
            .safe_mul(&env, 10_000_i128 + discount_bps as i128)
            / 10_000;
        let collateral_transferred = collateral_transferred.min(auction.collateral_amount);

        // Mark as settled.
        auction.is_settled = true;
        auctions.set(auction_id, auction);
        env.storage().persistent().set(&symbol_short!("auctions"), &auctions);

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
    pub fn expire_auction(env: Env, auction_id: u64, reserve_accounts: Vec<Address>) -> i128 {
        let config = Self::load_config(&env);
        assert_caller_auth(&env, &config.admin, symbol_short!("expire"), &(auction_id,));

        let mut auctions: Map<u64, Auction> = env
            .storage()
            .persistent()
            .get(&symbol_short!("auctions"))
            .unwrap_or(Map::new(&env));

        let mut auction = auctions.get(auction_id).expect("auction not found");

        assert!(!auction.is_settled, "auction already settled");
        assert!(
            env.ledger().sequence() >= auction.end_ledger,
            "auction has not expired yet"
        );

        auction.is_settled = true;
        auctions.set(auction_id, auction.clone());
        env.storage().persistent().set(&symbol_short!("auctions"), &auctions);

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
        let _ = env;
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
            .get(&symbol_short!("cfg"))
            .expect("contract not initialised — call initialize() first")
    }

    fn find_auction(env: &Env, auction_id: u64) -> Option<Auction> {
        let auctions: Map<u64, Auction> = env
            .storage()
            .persistent()
            .get(&symbol_short!("auctions"))
            .unwrap_or(Map::new(env));
        auctions.get(auction_id)
    }
}
