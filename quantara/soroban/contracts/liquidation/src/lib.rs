//! Liquidation auction contract for the Quantara protocol (issue #262).
//!
//! Implements a **Dutch-auction** liquidation mechanism. In a Dutch auction
//! the starting price is set above market (a premium) and decreases linearly
//! until a liquidator accepts the offer or a reserve price floor is reached.
//!
//! ## Auction lifecycle
//!
//! ```text
//! 1. protocol calls start_auction()   → auction registered, clock starts
//! 2. anyone calls current_price()     → reads the declining price curve
//! 3. liquidator calls bid()            → pays debt, receives collateral
//! 4. if no bid before end_ledger,
//!    protocol calls expire_auction()  → batch-distribute collateral, mark failed
//! ```
//!
//! ## Price model
//!
//! The auction prices the full collateral lot in units of debt. The price is
//! expressed in basis points of the par price, where `10_000` bps (1.0) means
//! the liquidator pays exactly `debt_amount` to receive the full
//! `collateral_amount`.
//!
//! The price declines linearly from `start_price_bps` (a premium ≥ 10_000) to
//! `min_price_bps` (the reserve floor ≤ 10_000) over `duration_ledgers`:
//!
//! ```text
//! price(t)  = start_price_bps - (start_price_bps - min_price_bps) * elapsed / duration
//! debt_paid = debt_amount * price(t) / 10_000
//! collateral_received = collateral_amount          (fixed lot, never inflated)
//! ```
//!
//! A liquidator therefore pays a premium early and a discount at the floor,
//! while the collateral delivered never exceeds the amount being auctioned.
//!
//! ## Settlement & custody
//!
//! `bid()` performs two Stellar Asset Contract transfers in one invocation:
//! first the liquidator's debt token is moved to this contract, then the
//! contract's collateral token is moved to the liquidator. Soroban invocation
//! atomicity guarantees either both legs complete or neither does, so a
//! settlement can never be half-applied. The contract must already hold the
//! collateral (custodying collateral into this contract is the caller's
//! responsibility and is out of scope here), and the liquidator must hold the
//! debt token being transferred.
//!
//! ## Batch liquidation
//!
//! When `expire_auction` is called on an un-bid auction the collateral is
//! **batch-distributed** pro-rata (floor division) to all registered reserve
//! accounts via `distribute_batch`; the division remainder (dust) is left in
//! the contract's balance.

#![no_std]

use soroban_sdk::{
    contract, contractimpl, contracttype, symbol_short, token, Address, Env, Map, Vec,
};

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
    /// Collateral token released to the liquidator (Stellar Asset Contract id).
    pub collateral_asset: Address,
    /// Debt token the liquidator must pay with (Stellar Asset Contract id).
    pub debt_asset: Address,
    /// Total collateral being auctioned (in base units).
    pub collateral_amount: i128,
    /// Total outstanding debt at par (in base units).
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
    /// Starting price in basis points of the par debt-per-collateral price.
    /// Must be ≥ 10_000 (a premium over par).
    pub start_price_bps: u32,
    /// Reserve floor price in basis points. Must be ≤ 10_000 (a discount to
    /// par) and > 0.
    pub min_price_bps: u32,
}

/// Result returned from `bid`.
#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BidResult {
    /// Collateral transferred to the liquidator.
    pub collateral_transferred: i128,
    /// Price (in basis points) at which the auction cleared.
    pub price_bps: u32,
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
        assert!(config.min_price_bps > 0, "min_price_bps must be > 0");
        assert!(
            config.start_price_bps >= config.min_price_bps,
            "start_price_bps must be >= min_price_bps"
        );
        assert!(
            config.start_price_bps >= 10_000,
            "start_price_bps must be >= 10_000 (premium over par)"
        );
        assert!(
            config.min_price_bps <= 10_000,
            "min_price_bps must be <= 10_000 (reserve floor)"
        );
        assert!(
            config.start_price_bps <= 20_000,
            "start_price_bps cannot exceed 20_000 (2x premium)"
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
    /// * `collateral_asset`   - Collateral token (Stellar Asset Contract) to release.
    /// * `debt_asset`         - Debt token the liquidator must pay with.
    /// * `collateral_amount`  - Collateral amount up for auction.
    /// * `debt_amount`        - Outstanding debt at par to be repaid by the winner.
    ///
    /// # Returns
    /// The ledger number at which the auction expires.
    pub fn start_auction(
        env: Env,
        auction_id: u64,
        debtor: Address,
        collateral_asset: Address,
        debt_asset: Address,
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
            collateral_asset,
            debt_asset,
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
            .set(&symbol_short!("auctions"), &updated);

        end_ledger
    }

    // ------------------------------------------------------------------
    // Price curve
    // ------------------------------------------------------------------

    /// Compute the current price (debt per collateral, in basis points) for an
    /// active auction.
    ///
    /// Returns `start_price_bps` if the auction has just started, and linearly
    /// interpolates down to `min_price_bps` as the auction approaches its end
    /// ledger. The reserve floor (`min_price_bps`) is returned once the auction
    /// has expired.
    ///
    /// Returns 0 if the auction is settled or does not exist.
    pub fn current_price(env: Env, auction_id: u64) -> u32 {
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
            return config.min_price_bps;
        }

        // Linear interpolation: price decreases as time progresses.
        let elapsed = current_ledger.saturating_sub(auction.start_ledger) as u64;
        let duration = auction.end_ledger.saturating_sub(auction.start_ledger) as u64;

        if duration == 0 {
            return config.min_price_bps;
        }

        let price_range = config.start_price_bps.saturating_sub(config.min_price_bps) as u64;

        let reduction = price_range.saturating_mul(elapsed) / duration;

        (config.start_price_bps as u64).saturating_sub(reduction) as u32
    }

    // ------------------------------------------------------------------
    // Liquidator: bid
    // ------------------------------------------------------------------

    /// Accept the current auction price and liquidate the position.
    ///
    /// The liquidator must hold `debt_amount * price / 10_000` of the debt
    /// token (transferred to this contract). On success the contract transfers
    /// the full collateral lot to the liquidator.
    ///
    /// Settlement is atomic: the debt leg is transferred first, then the
    /// collateral leg; a failure in either reverts the whole invocation, so
    /// the auction is only marked settled once both legs have completed.
    ///
    /// # Returns
    /// A `BidResult` with the collateral transferred and the clearing price.
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

        let price_bps = Self::current_price(env.clone(), auction_id);

        // The full collateral lot is always delivered; the declining price
        // determines how much debt the liquidator pays for it.
        let collateral_received = auction.collateral_amount;
        let debt_paid = auction.debt_amount.safe_mul(&env, price_bps as i128) / 10_000;
        assert!(debt_paid > 0, "debt payment must be positive");

        let contract = env.current_contract_address();

        // 1. Liquidator pays the debt token into the contract.
        token::TokenClient::new(&env, &auction.debt_asset).transfer(
            &liquidator,
            &contract,
            &debt_paid,
        );
        // 2. Contract releases the collateral token to the liquidator.
        token::TokenClient::new(&env, &auction.collateral_asset).transfer(
            &contract,
            &liquidator,
            &collateral_received,
        );

        // Mark as settled only after both legs have completed.
        auction.is_settled = true;
        auctions.set(auction_id, auction);
        env.storage()
            .persistent()
            .set(&symbol_short!("auctions"), &auctions);

        BidResult {
            collateral_transferred: collateral_received,
            price_bps,
        }
    }

    // ------------------------------------------------------------------
    // Admin: expire / batch distribute
    // ------------------------------------------------------------------

    /// Expire an auction that received no bids within its time window.
    ///
    /// The remaining collateral is batch-distributed pro-rata to the provided
    /// `reserve_accounts`; the division remainder (dust) stays in the
    /// contract's balance.
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

        // Disburse before marking settled so a failed transfer reverts the
        // whole invocation (Soroban atomicity).
        let share = Self::distribute_batch(
            &env,
            &auction.collateral_asset,
            auction.collateral_amount,
            reserve_accounts,
        );

        auction.is_settled = true;
        auctions.set(auction_id, auction);
        env.storage()
            .persistent()
            .set(&symbol_short!("auctions"), &auctions);

        share
    }

    /// Batch-distribute collateral pro-rata to reserve accounts.
    ///
    /// Each account receives `floor(collateral_amount / n)`; the remainder
    /// (`dust = collateral_amount - share * n`) is left in the contract's
    /// balance, so no collateral is silently destroyed or rounded away from
    /// the accounted total.
    ///
    /// Returns the per-account share.
    fn distribute_batch(
        env: &Env,
        collateral_asset: &Address,
        collateral_amount: i128,
        reserve_accounts: Vec<Address>,
    ) -> i128 {
        let n = reserve_accounts.len() as i128;
        if n == 0 {
            return 0;
        }

        let contract = env.current_contract_address();
        let token = token::TokenClient::new(env, collateral_asset);

        // Floor division: `share * n <= collateral_amount`, so the unspent
        // remainder (`collateral_amount - share * n`) stays in the contract.
        let share = collateral_amount / n;
        for account in reserve_accounts.iter() {
            token.transfer(&contract, &account, &share);
        }

        share
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

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    extern crate std;

    use super::*;
    use soroban_sdk::testutils::Address as _;
    use soroban_sdk::testutils::Ledger as _;
    use soroban_sdk::token::{StellarAssetClient, TokenClient};
    use soroban_sdk::vec;

    const START_PRICE_BPS: u32 = 10_500; // 5% premium over par
    const MIN_PRICE_BPS: u32 = 9_000; // 10% discount at the reserve floor
    const DURATION: u32 = 100;

    struct Fixture {
        env: Env,
        contract_id: Address,
        liquidator: Address,
        debtor: Address,
        collateral: Address,
        debt: Address,
    }

    fn setup() -> Fixture {
        let env = Env::default();
        env.mock_all_auths();

        let admin = Address::generate(&env);
        let liquidator = Address::generate(&env);
        let debtor = Address::generate(&env);

        let contract_id = env.register(LiquidationContract, ());
        let client = LiquidationContractClient::new(&env, &contract_id);
        client.initialize(
            &admin,
            &AuctionConfig {
                admin: admin.clone(),
                duration_ledgers: DURATION,
                start_price_bps: START_PRICE_BPS,
                min_price_bps: MIN_PRICE_BPS,
            },
        );

        // Two distinct Stellar Asset Contracts: one collateral, one debt.
        let collateral = env
            .register_stellar_asset_contract_v2(admin.clone())
            .address();
        let debt = env
            .register_stellar_asset_contract_v2(admin.clone())
            .address();

        Fixture {
            env,
            contract_id,
            liquidator,
            debtor,
            collateral,
            debt,
        }
    }

    fn start_auction(fx: &Fixture, auction_id: u64, collateral_amount: i128, debt_amount: i128) {
        let client = LiquidationContractClient::new(&fx.env, &fx.contract_id);
        client.start_auction(
            &auction_id,
            &fx.debtor,
            &fx.collateral,
            &fx.debt,
            &collateral_amount,
            &debt_amount,
        );
    }

    /// A full bid settlement moves the debt token from the liquidator into the
    /// contract and the collateral token from the contract into the liquidator,
    /// exactly the auctioned collateral amount (never more).
    #[test]
    fn test_bid_settles_and_transfers_tokens() {
        let fx = setup();

        // Contract holds the collateral; liquidator holds debt to pay with.
        StellarAssetClient::new(&fx.env, &fx.collateral).mint(&fx.contract_id, &1_000_i128);
        StellarAssetClient::new(&fx.env, &fx.debt).mint(&fx.liquidator, &2_000_i128);

        start_auction(&fx, 1, 1_000, 1_000);

        let client = LiquidationContractClient::new(&fx.env, &fx.contract_id);
        let result = client.bid(&fx.liquidator, &1u64);

        // At the start ledger the price is the premium: 1_050 bps over par
        // means debt_paid = 1_000 * 10_500 / 10_000 = 1_050.
        assert_eq!(result.price_bps, START_PRICE_BPS);
        assert_eq!(result.collateral_transferred, 1_000);

        let collateral_client = TokenClient::new(&fx.env, &fx.collateral);
        let debt_client = TokenClient::new(&fx.env, &fx.debt);

        // Liquidator paid 1_050 debt and received the full collateral lot.
        assert_eq!(debt_client.balance(&fx.liquidator), 950);
        assert_eq!(debt_client.balance(&fx.contract_id), 1_050);
        assert_eq!(collateral_client.balance(&fx.liquidator), 1_000);
        assert_eq!(collateral_client.balance(&fx.contract_id), 0);

        let auction = client.get_auction(&1u64).unwrap();
        assert!(
            auction.is_settled,
            "auction must be marked settled after bid"
        );
    }

    /// The price declines linearly from the starting premium to the reserve
    /// floor, and the floor is returned once the auction expires.
    #[test]
    fn test_price_declines_to_reserve_floor() {
        let fx = setup();
        start_auction(&fx, 1, 1_000, 1_000);

        let client = LiquidationContractClient::new(&fx.env, &fx.contract_id);

        // Auction opens at ledger 0 → price is the starting premium.
        assert_eq!(client.current_price(&1u64), START_PRICE_BPS);

        // Halfway through the 100-ledger duration.
        fx.env.ledger().set_sequence_number(DURATION / 2);
        assert_eq!(
            client.current_price(&1u64),
            (START_PRICE_BPS + MIN_PRICE_BPS) / 2
        );

        // At/after expiry the reserve floor is returned.
        fx.env.ledger().set_sequence_number(DURATION);
        assert_eq!(client.current_price(&1u64), MIN_PRICE_BPS);
    }

    /// A bid later in the auction pays less debt (the discount) while still
    /// receiving exactly the auctioned collateral — never more.
    #[test]
    fn test_bid_at_lower_price_pays_less_debt() {
        let fx = setup();

        StellarAssetClient::new(&fx.env, &fx.collateral).mint(&fx.contract_id, &1_000_i128);
        StellarAssetClient::new(&fx.env, &fx.debt).mint(&fx.liquidator, &2_000_i128);

        start_auction(&fx, 1, 1_000, 1_000);

        // Bid halfway: price = 9_750 bps → debt_paid = 1_000 * 9_750 / 10_000 = 975.
        fx.env.ledger().set_sequence_number(DURATION / 2);
        let client = LiquidationContractClient::new(&fx.env, &fx.contract_id);
        let result = client.bid(&fx.liquidator, &1u64);

        assert_eq!(result.price_bps, (START_PRICE_BPS + MIN_PRICE_BPS) / 2);
        assert_eq!(result.collateral_transferred, 1_000);

        let collateral_client = TokenClient::new(&fx.env, &fx.collateral);
        let debt_client = TokenClient::new(&fx.env, &fx.debt);

        assert_eq!(debt_client.balance(&fx.liquidator), 1_025);
        assert_eq!(debt_client.balance(&fx.contract_id), 975);
        assert_eq!(collateral_client.balance(&fx.liquidator), 1_000);
        assert_eq!(collateral_client.balance(&fx.contract_id), 0);
    }

    /// An expired auction disburses collateral pro-rata to reserve accounts
    /// with floor division; the remainder (dust) stays in the contract.
    #[test]
    fn test_expire_auction_distributes_batch_pro_rata() {
        let fx = setup();

        StellarAssetClient::new(&fx.env, &fx.collateral).mint(&fx.contract_id, &1_000_i128);

        start_auction(&fx, 1, 1_000, 1_000);

        // Expire the auction.
        fx.env.ledger().set_sequence_number(DURATION + 1);

        let r1 = Address::generate(&fx.env);
        let r2 = Address::generate(&fx.env);
        let r3 = Address::generate(&fx.env);
        let reserve = vec![&fx.env, r1.clone(), r2.clone(), r3.clone()];

        let client = LiquidationContractClient::new(&fx.env, &fx.contract_id);
        let share = client.expire_auction(&1u64, &reserve);

        // 1_000 / 3 = 333 per account, dust = 1 stays in the contract.
        assert_eq!(share, 333);

        let collateral_client = TokenClient::new(&fx.env, &fx.collateral);
        assert_eq!(collateral_client.balance(&r1), 333);
        assert_eq!(collateral_client.balance(&r2), 333);
        assert_eq!(collateral_client.balance(&r3), 333);
        assert_eq!(collateral_client.balance(&fx.contract_id), 1);

        let auction = client.get_auction(&1u64).unwrap();
        assert!(
            auction.is_settled,
            "auction must be marked settled after expiry"
        );
    }
}
