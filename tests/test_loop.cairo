use alexandria_math::fast_power::fast_power;
use core::panic_with_felt252;
use ekubo::interfaces::core::{SwapParameters, ICoreDispatcher, ICoreDispatcherTrait};
use ekubo::types::i129::{i129};
use ekubo::types::keys::{PoolKey};
use openzeppelin_token::erc20::interface::{ERC20ABIDispatcher, ERC20ABIDispatcherTrait};

use pragma_lib::abi::{IPragmaABIDispatcher, IPragmaABIDispatcherTrait};
use pragma_lib::types::{AggregationMode, DataType, PragmaPricesResponse};
use snforge_std::cheatcodes::execution_info::account_contract_address::{
    start_cheat_account_contract_address, stop_cheat_account_contract_address
};
use snforge_std::cheatcodes::execution_info::block_timestamp::{
    start_cheat_block_timestamp, stop_cheat_block_timestamp
};
use snforge_std::cheatcodes::execution_info::caller_address::{
    start_cheat_caller_address, stop_cheat_caller_address
};
use snforge_std::{declare, DeclareResultTrait, ContractClassTrait};
use spotnet::interfaces::{
    IDepositDispatcher, IDepositSafeDispatcher, IDepositSafeDispatcherTrait, IDepositDispatcherTrait
};
use spotnet::types::{DepositData, Claim};

use starknet::{ContractAddress, get_caller_address, get_block_number, get_block_timestamp};

use super::interfaces::{IMarketTestingDispatcher, IMarketTestingDispatcherTrait};

mod contracts {
    pub const EKUBO_CORE_MAINNET: felt252 =
        0x00000005dd3d2f4429af886cd1a3b08289dbcea99a294197e9eb43b0e0325b4b;

    pub const ZKLEND_MARKET: felt252 =
        0x04c0a5193d58f74fbace4b74dcf65481e734ed1714121bdc571da345540efa05;

    pub const PRAGMA_ADDRESS: felt252 =
        0x02a85bd616f912537c50a49a4076db02c00b29b2cdc8a197ce92ed1837fa875b;
}

mod tokens {
    pub const ETH: felt252 = 0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7;
    pub const USDC: felt252 = 0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8;
}

fn deploy_deposit_contract(user: ContractAddress) -> ContractAddress {
    let deposit_contract = declare("Deposit").unwrap().contract_class();
    let (deposit_address, _) = deposit_contract
        .deploy(
            @array![
                user.try_into().unwrap(), contracts::EKUBO_CORE_MAINNET, contracts::ZKLEND_MARKET
            ]
        )
        .expect('Deploy failed');
    deposit_address
}

fn get_deposit_dispatcher(user: ContractAddress) -> IDepositDispatcher {
    IDepositDispatcher { contract_address: deploy_deposit_contract(user) }
}

fn get_safe_deposit_dispatcher(user: ContractAddress) -> IDepositSafeDispatcher {
    IDepositSafeDispatcher { contract_address: deploy_deposit_contract(user) }
}

fn get_asset_price_pragma(pair: felt252) -> u128 {
    let oracle_dispatcher = IPragmaABIDispatcher {
        contract_address: contracts::PRAGMA_ADDRESS.try_into().unwrap()
    };
    let output: PragmaPricesResponse = oracle_dispatcher
        .get_data(DataType::SpotEntry(pair), AggregationMode::Median(()));
    output.price / 100 // Make 6 decimals wide instead of 8.
}

// fn get_token_addresses(pair: felt252) -> (ContractAddress, ContractAddress) {
//     match pair {
//         'ETH/USDC' => (tokens::ETH.try_into().unwrap(), tokens::USDC.try_into().unwrap()),
//         _ => (0.try_into().unwrap(), 1.try_into().unwrap()),
//     }
// }

// TODO: Add tests for asserts.

#[test]
#[fork("MAINNET")]
fn test_loop_eth_valid() {
    let usdc_addr: ContractAddress =
        0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
        .try_into()
        .unwrap();
    let eth_addr: ContractAddress =
        0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
        .try_into()
        .unwrap();
    let user: ContractAddress = 0x059a943ca214c10234b9a3b61c558ac20c005127d183b86a99a8f3c60a08b4ff
        .try_into()
        .unwrap();

    let pool_key = PoolKey {
        token0: eth_addr,
        token1: usdc_addr,
        fee: 170141183460469235273462165868118016,
        tick_spacing: 1000,
        extension: 0.try_into().unwrap()
    };
    let pool_price = get_asset_price_pragma('ETH/USD').into();
    let token_disp = ERC20ABIDispatcher { contract_address: eth_addr };
    let deposit_disp = get_deposit_dispatcher(user);
    start_cheat_caller_address(eth_addr.try_into().unwrap(), user);
    token_disp.approve(deposit_disp.contract_address, 685000000000000);
    stop_cheat_caller_address(eth_addr);

    start_cheat_account_contract_address(deposit_disp.contract_address, user);
    deposit_disp
        .loop_liquidity(
            DepositData { token: eth_addr, amount: 685000000000000, multiplier: 4 },
            pool_key,
            pool_price,
            pool_price
        );
    stop_cheat_account_contract_address(deposit_disp.contract_address);
}

#[test]
#[fuzzer(runs: 10)]
#[feature("safe_dispatcher")]
#[fork("MAINNET")]
fn test_loop_eth_fuzz(amount: u64) {
    let usdc_addr: ContractAddress =
        0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
        .try_into()
        .unwrap();
    let eth_addr: ContractAddress =
        0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
        .try_into()
        .unwrap();
    let user: ContractAddress = 0x059a943ca214c10234b9a3b61c558ac20c005127d183b86a99a8f3c60a08b4ff
        .try_into()
        .unwrap();
    let pool_key = PoolKey {
        token0: eth_addr,
        token1: usdc_addr,
        fee: 170141183460469235273462165868118016,
        tick_spacing: 1000,
        extension: 0.try_into().unwrap()
    };

    let pool_price = get_asset_price_pragma('ETH/USD').into();
    let token_disp = ERC20ABIDispatcher { contract_address: eth_addr };
    let deposit_disp = get_safe_deposit_dispatcher(user);

    start_cheat_caller_address(eth_addr.try_into().unwrap(), user);
    token_disp.approve(deposit_disp.contract_address, amount.into());
    stop_cheat_caller_address(eth_addr);

    start_cheat_account_contract_address(deposit_disp.contract_address, user);
    if let Result::Err(panic_data) = deposit_disp
        .loop_liquidity(
            DepositData { token: eth_addr, amount: amount.into(), multiplier: 4 },
            pool_key,
            pool_price,
            pool_price
        ) {
        let message = *panic_data.at(0);
        assert(
            message == 'Parameters cannot be zero'
                || message == 'Loop amount is too small'
                || message == 'Approved amount incuficient'
                || message == 'Insufficient balance',
            message
        ); // Acceptable panics which can be triggered by fuzzers' values
    };
    stop_cheat_account_contract_address(deposit_disp.contract_address);
}

#[test]
#[fork("MAINNET")]
fn test_loop_usdc_valid() {
    let usdc_addr: ContractAddress =
        0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
        .try_into()
        .unwrap();
    let eth_addr: ContractAddress =
        0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
        .try_into()
        .unwrap();
    let user = 0x0038925b0bcf4dce081042ca26a96300d9e181b910328db54a6c89e5451503f5
        .try_into()
        .unwrap();

    let pool_key = PoolKey {
        token0: eth_addr,
        token1: usdc_addr,
        fee: 170141183460469235273462165868118016,
        tick_spacing: 1000,
        extension: 0.try_into().unwrap()
    };

    let token_disp = ERC20ABIDispatcher { contract_address: usdc_addr };
    let decimals_sum_power: u128 = fast_power(
        10,
        (ERC20ABIDispatcher { contract_address: eth_addr }.decimals() + token_disp.decimals())
            .into()
    );
    let pool_price = 1 * decimals_sum_power.into() / get_asset_price_pragma('ETH/USD');
    let deposit_disp = get_deposit_dispatcher(user);
    start_cheat_caller_address(usdc_addr.try_into().unwrap(), user);
    token_disp.approve(deposit_disp.contract_address, 60000000);
    stop_cheat_caller_address(usdc_addr);

    start_cheat_account_contract_address(deposit_disp.contract_address, user);
    deposit_disp
        .loop_liquidity(
            DepositData { token: usdc_addr, amount: 60000000, multiplier: 4 },
            pool_key,
            pool_price.into(),
            1000000
        );
    stop_cheat_account_contract_address(deposit_disp.contract_address);
}

#[test]
#[should_panic(expected: 'Caller is not the owner')]
#[fork("MAINNET")]
fn test_loop_unauthorized() {
    let usdc_addr: ContractAddress =
        0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
        .try_into()
        .unwrap();
    let eth_addr: ContractAddress =
        0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
        .try_into()
        .unwrap();
    let user = 0x0038925b0bcf4dce081042ca26a96300d9e181b910328db54a6c89e5451503f5
        .try_into()
        .unwrap();

    let pool_key = PoolKey {
        token0: eth_addr,
        token1: usdc_addr,
        fee: 170141183460469235273462165868118016,
        tick_spacing: 1000,
        extension: 0.try_into().unwrap()
    };

    let decimals_sum_power: u128 = fast_power(
        10,
        (ERC20ABIDispatcher { contract_address: eth_addr }.decimals()
            + ERC20ABIDispatcher { contract_address: usdc_addr }.decimals())
            .into()
    );
    let pool_price = 1 * decimals_sum_power.into() / get_asset_price_pragma('ETH/USD');

    let disp = get_deposit_dispatcher(user);

    disp
        .loop_liquidity(
            DepositData { token: usdc_addr, amount: 10000000, multiplier: 4 },
            pool_key,
            pool_price.into(),
            1000000
        );
}

#[test]
#[should_panic(expected: 'Open position already exists')]
#[fork("MAINNET")]
fn test_loop_position_exists() {
    let usdc_addr: ContractAddress =
        0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
        .try_into()
        .unwrap();
    let eth_addr: ContractAddress =
        0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
        .try_into()
        .unwrap();
    let user = 0x0038925b0bcf4dce081042ca26a96300d9e181b910328db54a6c89e5451503f5
        .try_into()
        .unwrap();

    let pool_key = PoolKey {
        token0: eth_addr,
        token1: usdc_addr,
        fee: 170141183460469235273462165868118016,
        tick_spacing: 1000,
        extension: 0.try_into().unwrap()
    };

    let token_disp = ERC20ABIDispatcher { contract_address: usdc_addr };
    let decimals_sum_power: u128 = fast_power(
        10,
        (ERC20ABIDispatcher { contract_address: eth_addr }.decimals() + token_disp.decimals())
            .into()
    );
    let pool_price = 1 * decimals_sum_power.into() / get_asset_price_pragma('ETH/USD');
    let deposit_disp = get_deposit_dispatcher(user);
    start_cheat_caller_address(usdc_addr.try_into().unwrap(), user);
    token_disp.approve(deposit_disp.contract_address, 60000000);
    stop_cheat_caller_address(usdc_addr);

    start_cheat_account_contract_address(deposit_disp.contract_address, user);
    deposit_disp
        .loop_liquidity(
            DepositData { token: usdc_addr, amount: 60000000, multiplier: 4 },
            pool_key,
            pool_price.into(),
            1000000
        );
    deposit_disp
        .loop_liquidity(
            DepositData { token: usdc_addr, amount: 60000000, multiplier: 4 },
            pool_key,
            pool_price.into(),
            1000000
        );
    stop_cheat_account_contract_address(deposit_disp.contract_address);
}

#[test]
#[fuzzer(runs: 10)]
#[feature("safe_dispatcher")]
#[fork("MAINNET")]
fn test_loop_position_exists_fuzz(amount: u64) {
    let usdc_addr: ContractAddress =
        0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
        .try_into()
        .unwrap();
    let eth_addr: ContractAddress =
        0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
        .try_into()
        .unwrap();
    let user: ContractAddress = 0x059a943ca214c10234b9a3b61c558ac20c005127d183b86a99a8f3c60a08b4ff
        .try_into()
        .unwrap();
    let pool_key = PoolKey {
        token0: eth_addr,
        token1: usdc_addr,
        fee: 170141183460469235273462165868118016,
        tick_spacing: 1000,
        extension: 0.try_into().unwrap()
    };

    let pool_price = get_asset_price_pragma('ETH/USD').into();
    let token_disp = ERC20ABIDispatcher { contract_address: eth_addr };
    let deposit_disp = get_safe_deposit_dispatcher(user);

    start_cheat_caller_address(eth_addr.try_into().unwrap(), user);
    token_disp.approve(deposit_disp.contract_address, amount.into());
    stop_cheat_caller_address(eth_addr);

    start_cheat_account_contract_address(deposit_disp.contract_address, user);

    if let Result::Err(_) = deposit_disp
        .loop_liquidity(
            DepositData { token: eth_addr, amount: amount.into(), multiplier: 2 },
            pool_key,
            pool_price,
            pool_price
        ) {
        return;
    };
    match deposit_disp
        .loop_liquidity(
            DepositData { token: eth_addr, amount: amount.into(), multiplier: 2 },
            pool_key,
            pool_price,
            pool_price
        ) {
        Result::Ok(_) => panic_with_felt252('Not panicked with position open'),
        Result::Err(panic_data) => assert(
            *panic_data.at(0) == 'Open position already exists', *panic_data.at(0)
        )
    };
    stop_cheat_account_contract_address(deposit_disp.contract_address);
}

#[test]
#[fork("MAINNET")]
fn test_close_position_usdc_valid_time_passed() {
    let usdc_addr: ContractAddress =
        0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
        .try_into()
        .unwrap();
    let eth_addr: ContractAddress =
        0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
        .try_into()
        .unwrap();
    let user: ContractAddress = 0x0038925b0bcf4dce081042ca26a96300d9e181b910328db54a6c89e5451503f5
        .try_into()
        .unwrap();

    let pool_key = PoolKey {
        token0: eth_addr,
        token1: usdc_addr,
        fee: 170141183460469235273462165868118016,
        tick_spacing: 1000,
        extension: 0.try_into().unwrap()
    };
    let quote_token_price = get_asset_price_pragma('ETH/USD').into();

    let token_disp = ERC20ABIDispatcher { contract_address: usdc_addr };
    let initial_balance = token_disp.balanceOf(user);
    // println!("Initial bal {initial_balance}");
    let decimals_sum_power: u128 = fast_power(
        10,
        (ERC20ABIDispatcher { contract_address: eth_addr }.decimals() + token_disp.decimals())
            .into()
    );
    let pool_price = 1 * decimals_sum_power.into() / quote_token_price;
    let deposit_disp = get_deposit_dispatcher(user);

    start_cheat_caller_address(usdc_addr.try_into().unwrap(), user);
    token_disp.approve(deposit_disp.contract_address, 1000000000);
    stop_cheat_caller_address(usdc_addr);

    start_cheat_account_contract_address(deposit_disp.contract_address, user);
    deposit_disp
        .loop_liquidity(
            DepositData { token: usdc_addr, amount: 1000000000, multiplier: 4 },
            pool_key,
            pool_price,
            pool_price
        );
    stop_cheat_account_contract_address(deposit_disp.contract_address);
    let zk_market = IMarketTestingDispatcher {
        contract_address: contracts::ZKLEND_MARKET.try_into().unwrap()
    };
    let usdc_reserve = zk_market.get_reserve_data(usdc_addr);
    let eth_reserve = zk_market.get_reserve_data(eth_addr);
    let (lending_rate, borrowing_rate): (u256, u256) = (
        usdc_reserve.current_lending_rate.into(), eth_reserve.current_borrowing_rate.into()
    );
    // println!("{}", lending_rate);
    // println!("{}", borrowing_rate);
    start_cheat_account_contract_address(deposit_disp.contract_address, user);
    start_cheat_block_timestamp(
        contracts::ZKLEND_MARKET.try_into().unwrap(), get_block_timestamp() + 40000000
    );
    // println!("Debt {}", zk_market.get_user_debt_for_token(deposit_disp.contract_address,
    // eth_addr));
    // println!("Z bal {}", ERC20ABIDispatcher {contract_address:
    // usdc_reserve.z_token_address}.balanceOf(deposit_disp.contract_address));
    deposit_disp.close_position(usdc_addr, eth_addr, pool_key, pool_price, quote_token_price);

    stop_cheat_block_timestamp(contracts::ZKLEND_MARKET.try_into().unwrap());
    stop_cheat_account_contract_address(deposit_disp.contract_address);
    // println!("After bal {}", token_disp.balanceOf(user));
    assert(token_disp.balanceOf(user) > initial_balance, 'Balance is in wrong state');
}

#[test]
#[fork("MAINNET")]
fn test_close_position_amounts_cleared() {
    let usdc_addr: ContractAddress =
        0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
        .try_into()
        .unwrap();
    let eth_addr: ContractAddress =
        0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
        .try_into()
        .unwrap();
    let user: ContractAddress = 0x0038925b0bcf4dce081042ca26a96300d9e181b910328db54a6c89e5451503f5
        .try_into()
        .unwrap();

    let pool_key = PoolKey {
        token0: eth_addr,
        token1: usdc_addr,
        fee: 170141183460469235273462165868118016,
        tick_spacing: 1000,
        extension: 0.try_into().unwrap()
    };
    let quote_token_price = get_asset_price_pragma('ETH/USD').into();

    let token_disp = ERC20ABIDispatcher { contract_address: usdc_addr };
    let decimals_sum_power: u128 = fast_power(
        10,
        (ERC20ABIDispatcher { contract_address: eth_addr }.decimals() + token_disp.decimals())
            .into()
    );
    let pool_price = 1 * decimals_sum_power.into() / quote_token_price;
    let deposit_disp = get_deposit_dispatcher(user);

    start_cheat_caller_address(usdc_addr.try_into().unwrap(), user);
    token_disp.approve(deposit_disp.contract_address, 1000000000);
    stop_cheat_caller_address(usdc_addr);

    start_cheat_account_contract_address(deposit_disp.contract_address, user);
    deposit_disp
        .loop_liquidity(
            DepositData { token: usdc_addr, amount: 1000000000, multiplier: 4 },
            pool_key,
            pool_price,
            pool_price
        );
    stop_cheat_account_contract_address(deposit_disp.contract_address);
    let zk_market = IMarketTestingDispatcher {
        contract_address: contracts::ZKLEND_MARKET.try_into().unwrap()
    };
    start_cheat_account_contract_address(deposit_disp.contract_address, user);
    deposit_disp.close_position(usdc_addr, eth_addr, pool_key, pool_price, quote_token_price);
    stop_cheat_account_contract_address(deposit_disp.contract_address);

    assert(
        zk_market.get_user_debt_for_token(deposit_disp.contract_address, eth_addr) == 0,
        'Debt remains after repay'
    );
    assert(
        ERC20ABIDispatcher {
            contract_address: zk_market.get_reserve_data(usdc_addr).z_token_address
        }
            .balanceOf(deposit_disp.contract_address) == 0,
        'Not all withdrawn'
    );
}

#[test]
#[fork("MAINNET", block_number: 834899)]
fn test_claim_rewards() {
    let strk_addr: ContractAddress =
        0x04718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d
        .try_into()
        .unwrap();

    let usdc_addr: ContractAddress =
        0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
        .try_into()
        .unwrap();
    let eth_addr: ContractAddress =
        0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
        .try_into()
        .unwrap();

    let user: ContractAddress = 0x20281104e6cb5884dabcdf3be376cf4ff7b680741a7bb20e5e07c26cd4870af
        .try_into()
        .unwrap();

    let pool_key = PoolKey {
        token0: eth_addr,
        token1: usdc_addr,
        fee: 170141183460469235273462165868118016,
        tick_spacing: 1000,
        extension: 0.try_into().unwrap()
    };

    let claim_data = Claim { id: 10611, claimee: user, amount: 0x2d86724a27dc3e2 };

    let proofs = [
        0x5e3a0851fc0f58fc98964fa4aeccfae6170f87540fb6c98c6b1a95ff8619235,
        0x2d6dc4884ec2fe892aeb92c661de4bd41a833603f309a2ca4079647f8bfc2d1,
        0x73a528ae05f2995cfecb744ffd6a9dd8e4697fb5fd65a6ee8bcdf3f7dba924d,
        0x6d4d65e6140674f5aa8aad2da4110faec2aba7a4b80080468a5068b5d8bfa55,
        0x58d3abc98b3aad194393f72f3be4f71636b2af39272e1ac4cae588ac5569e95,
        0x2d45d9ea573b7e830e182feaaf67fb9296080cdf8877ad787e8cd13a219c187,
        0x7fdc8c1b9a2303764f692d208ba6725a57db5e542f92b4dffeaebd00b495bb9,
        0x321c1fb2c1b85728f374568de28e173a220d2e0efcc404c7a7cd39883b0c8f7,
        0x151cfa61a31b61e7e8dedb909c6dbb13259404d8f413796e1c285ef8908a18b,
        0x45cbbc33878e5728fc97fb00c722a5946087c6f2ac287a15fa5abfa407b4d7d,
        0x194a2043aff310ac94defa8f50d78d66d63076a521c5fd7e2420c9b10a66813,
        0x3877f5b4750b7cb26e211e2f867882680bf9a9542222971f048fb831e6f225a,
        0x5c4a8fbdc17983b19b841f490aa0531d274e9a42231d22be2dadfbce6cdf981,
        0x44692783f2e911b439cd018f3ba8c067ba5ab88bec4b35e2496b2a3b0f817ef
    ].span();

    let pool_price: u256 = get_asset_price_pragma('ETH/USD').into();

    let strk_disp = ERC20ABIDispatcher { contract_address: strk_addr };
    let eth_disp = ERC20ABIDispatcher { contract_address: eth_addr };
    let deposit_disp = get_deposit_dispatcher(user);

    start_cheat_caller_address(eth_addr.try_into().unwrap(), user);
    eth_disp.approve(deposit_disp.contract_address, 685000000000000);
    stop_cheat_caller_address(eth_addr);

    start_cheat_account_contract_address(deposit_disp.contract_address, user);
    deposit_disp
        .loop_liquidity(
            DepositData { token: eth_addr, amount: 685000000000000, multiplier: 4 },
            pool_key,
            pool_price,
            pool_price
        );
    stop_cheat_account_contract_address(deposit_disp.contract_address);

    let initial_balance = strk_disp.balanceOf(user);
    // println!("initial bal {}", initial_balance);

    deposit_disp.claim_rewards(claim_data: claim_data, proofs: proofs);

    let final_balance = strk_disp.balanceOf(user);
    // println!("final bal {}", final_balance);

    assert(final_balance > initial_balance, 'Reward was not transferred');
    assert(final_balance - initial_balance == claim_data.amount.into(), 'Unexpected amount was rewarded');
}
// TODO: Calculate interest rates to test behaviour after liquidation.

// #[test]
// #[fork("MAINNET")]
// fn test_full_liquidation() {
//     let usdc_addr: ContractAddress =
//         0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
//         .try_into()
//         .unwrap();
//     let eth_addr: ContractAddress =
//         0x49d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
//         .try_into()
//         .unwrap();
//     let user: ContractAddress =
//     0x0038925b0bcf4dce081042ca26a96300d9e181b910328db54a6c89e5451503f5
//         .try_into()
//         .unwrap();
//     let liquidator: ContractAddress =
//     0x059a943ca214c10234b9a3b61c558ac20c005127d183b86a99a8f3c60a08b4ff.try_into().unwrap();

//     let pool_key = PoolKey {
//         token0: eth_addr,
//         token1: usdc_addr,
//         fee: 170141183460469235273462165868118016,
//         tick_spacing: 1000,
//         extension: 0.try_into().unwrap()
//     };
//     let pool_price = get_asset_price_pragma('ETH/USD').into();

//     let token_disp = ERC20ABIDispatcher { contract_address: eth_addr };
//     let initial_balance = token_disp.balanceOf(user);
//     let decimals_sum_power: u128 = fast_power(
//         10,
//         (ERC20ABIDispatcher { contract_address: eth_addr }.decimals() + token_disp.decimals())
//             .into()
//     );
//     let quote_token_price = 1 * decimals_sum_power.into() / pool_price;
//     let deposit_disp = get_deposit_dispatcher(user);

//     start_cheat_caller_address(eth_addr.try_into().unwrap(), user);
//     token_disp.approve(deposit_disp.contract_address, 10000000000000000);
//     stop_cheat_caller_address(eth_addr);

//     start_cheat_account_contract_address(deposit_disp.contract_address, user);
//     deposit_disp
//         .loop_liquidity(
//             DepositData { token: eth_addr, amount: 10000000000000000, multiplier: 4 },
//             pool_key,
//             pool_price,
//             pool_price
//         );
//     stop_cheat_account_contract_address(deposit_disp.contract_address);
//     let zk_market = IMarketTestingDispatcher {contract_address:
//     contracts::ZKLEND_MARKET.try_into().unwrap()};
//     let usdc_reserve = zk_market.get_reserve_data(usdc_addr);
//     let eth_reserve = zk_market.get_reserve_data(eth_addr);
//     let (lending_rate, borrowing_rate): (u256, u256) = (eth_reserve.current_lending_rate.into(),
//     usdc_reserve.current_borrowing_rate.into());

//     start_cheat_account_contract_address(deposit_disp.contract_address, user);

//     start_cheat_block_timestamp(contracts::ZKLEND_MARKET.try_into().unwrap(),
//     get_block_timestamp() + 4000000000);

//     start_cheat_caller_address(zk_market.contract_address, liquidator);

//     let debt = zk_market.get_user_debt_for_token(deposit_disp.contract_address,
//     usdc_addr).into();

//     start_cheat_caller_address(usdc_addr, liquidator);
//     ERC20ABIDispatcher {contract_address: usdc_addr}.approve(zk_market.contract_address, debt);
//     stop_cheat_caller_address(usdc_addr);
//     zk_market.liquidate(deposit_disp.contract_address, usdc_addr, (debt / 4).try_into().unwrap(),
//     eth_addr);
//     stop_cheat_caller_address(zk_market.contract_address);
//     // deposit_disp.close_position(eth_addr, usdc_addr, pool_key, pool_price, quote_token_price);

//     stop_cheat_block_timestamp(contracts::ZKLEND_MARKET.try_into().unwrap());

//     stop_cheat_account_contract_address(deposit_disp.contract_address);
// }


