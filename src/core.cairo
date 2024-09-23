use ekubo::types::keys::PoolKey;
use spotnet::types::{SwapData, SwapResult, DepositData, DepositsHistory};
use starknet::{ContractAddress};

#[starknet::interface]
pub trait ICore<TContractState> {
    fn swap(ref self: TContractState, swap_data: SwapData) -> SwapResult;

    fn loop_liquidity(
        ref self: TContractState,
        deposit_data: DepositData,
        pool_key: PoolKey,
        pool_price: u256,
        caller: ContractAddress
    );

    fn get_deposits_data(self: @TContractState) -> DepositsHistory;
}

#[starknet::contract]
pub mod Core {
    use ekubo::components::shared_locker::handle_delta;
    use ekubo::interfaces::core::SwapParameters;
    use ekubo::interfaces::core::{ICoreDispatcher, ICoreDispatcherTrait, ILocker};
    use ekubo::types::i129::i129;
    use ekubo::types::keys::PoolKey;
    use spotnet::constants::ZK_PERCENTS_DECIMALS;

    use spotnet::interfaces::{
        IMarketDispatcher, IMarketDispatcherTrait, IERC20Dispatcher, IERC20DispatcherTrait
    };
    use spotnet::types::{SwapData, SwapResult, DepositData, DepositsHistory};
    use starknet::event::EventEmitter;

    use starknet::storage::StoragePointerReadAccess;
    use starknet::storage::StoragePointerWriteAccess;
    use starknet::storage::{Vec, MutableVecTrait, VecTrait};
    use starknet::{ContractAddress};
    use starknet::{get_contract_address};
    use super::{ICore};

    #[storage]
    struct Storage {
        ekubo_core: ICoreDispatcher,
        zk_market: IMarketDispatcher,
        deposits: Vec<(ContractAddress, u256)>,
        borrows: Vec<(ContractAddress, u256)>
    }

    #[constructor]
    fn constructor(
        ref self: ContractState, ekubo_core: ICoreDispatcher, zk_market: IMarketDispatcher
    ) {
        self.ekubo_core.write(ekubo_core);
        self.zk_market.write(zk_market);
    }

    #[derive(starknet::Event, Drop)]
    struct LiquidityLooped {
        initial_amount: u256,
        deposited: u256,
        token_deposit: ContractAddress,
        borrowed: u256,
        token_borrowed: ContractAddress
    }

    #[event]
    #[derive(Drop, starknet::Event)]
    enum Event {
        LiquidityLooped: LiquidityLooped
    }

    fn div(a: u256, b: u256) -> felt252 {
        assert(b != 0, 'zero division');

        let a: u256 = a.into();
        let b: u256 = b.into();
        let quotient = a / b;

        quotient.try_into().unwrap()
    }

    fn get_borrow_amount(
        borrow_capacity: u256, token_price: u256, decimals_difference: u256, total_borrowed: u256
    ) -> felt252 {
        let borrow_const = 80;
        let amount_base_token = token_price * borrow_capacity;
        let amount_quote_token = amount_base_token / decimals_difference;
        div(amount_quote_token - total_borrowed, 100) * borrow_const
    }

    fn get_left_integer(number: u256) -> u256 {
        let mut temp_num = number;
        while temp_num > 9 {
            temp_num = temp_num / 10;
        };
        temp_num
    }

    fn pow(number: u256, power: u256) -> u256 {
        let mut temp = 0;
        if power == 0 {
            return 1;
        }
        temp = pow(number, power / 2);
        if (power % 2) == 0 {
            temp * temp
        } else {
            temp * temp * number
        }
    }

    #[abi(embed_v0)]
    impl CoreImpl of ICore<ContractState> {
        fn swap(ref self: ContractState, swap_data: SwapData) -> SwapResult {
            if swap_data.caller != get_contract_address() { // if called externally just for swap
                let token_disp = IERC20Dispatcher {
                    contract_address: if swap_data.params.is_token1 {
                        swap_data.pool_key.token1
                    } else {
                        swap_data.pool_key.token0
                    }
                };
                token_disp
                    .transferFrom(
                        swap_data.caller,
                        get_contract_address(),
                        swap_data.params.amount.mag.try_into().unwrap()
                    );
            }
            // Ekubo Callback
            ekubo::components::shared_locker::call_core_with_callback(
                self.ekubo_core.read(), @swap_data
            )
        }

        fn get_deposits_data(
            self: @ContractState
        ) -> DepositsHistory { // TODO: Refactor data obtaining
            let deposits_len = self.deposits.len();
            let borrows_len = self.borrows.len();
            let mut i = 0;
            let mut deposits: Array<(ContractAddress, u256)> = ArrayTrait::new();
            let mut borrows: Array<(ContractAddress, u256)> = ArrayTrait::new();
            while i < deposits_len {
                deposits.append(self.deposits.get(i).unwrap().read());
                i += 1;
            };
            i = 0;
            while i < borrows_len {
                borrows.append(self.borrows.get(i).unwrap().read());
                i += 1;
            };
            DepositsHistory { deposited: deposits.span(), borrowed: borrows.span() }
        }

        fn loop_liquidity(
            ref self: ContractState,
            deposit_data: DepositData,
            pool_key: PoolKey,
            pool_price: u256,
            caller: ContractAddress
        ) {
            let DepositData { token, amount, multiplier } = deposit_data;
            assert(multiplier < 5, 'Not supported');
            let token_dispatcher = IERC20Dispatcher { contract_address: token };
            let zk_market = self.zk_market.read();
            let is_token1 = token == pool_key.token0;
            let (borrowing_token, sqrt_limit) = if is_token1 {
                (pool_key.token1, 6277100250585753475930931601400621808602321654880405518632)
            } else {
                (pool_key.token0, 18446748437148339061)
            };
            let curr_contract_address = get_contract_address();

            token_dispatcher.transferFrom(caller, curr_contract_address, amount);
            let reserve_data = zk_market.get_reserve_data(token);

            let collateral_factor: u256 = reserve_data.collateral_factor.into();

            zk_market.enable_collateral(token);

            let deposit_token_decimals = pow(10, token_dispatcher.decimals().try_into().unwrap());
            token_dispatcher.approve(zk_market.contract_address, amount);
            zk_market.deposit(token, amount.try_into().expect('Overflow'));
            let mut deposited = amount;
            let mut total_borrowed = 0;
            let mut accumulated = 0;
            let mut i = 0;

            while (amount + accumulated) / amount < multiplier.into() {
                let borrow_capacity = div(deposited * collateral_factor, ZK_PERCENTS_DECIMALS)
                    .into();
                let to_borrow = get_borrow_amount(
                    borrow_capacity, pool_price, deposit_token_decimals, total_borrowed.into()
                );
                total_borrowed += to_borrow;
                zk_market.borrow(borrowing_token, to_borrow);

                let params = SwapParameters {
                    amount: i129 { mag: to_borrow.try_into().unwrap(), sign: false },
                    is_token1,
                    sqrt_ratio_limit: sqrt_limit,
                    skip_ahead: 0
                };
                let swapped_delta = self
                    .swap(SwapData { params, caller: curr_contract_address, pool_key })
                    .delta;
                let amount_swapped = if is_token1 {
                    swapped_delta.amount0.mag.into()
                } else {
                    swapped_delta.amount1.mag.into()
                };

                token_dispatcher.approve(zk_market.contract_address, amount_swapped.into());
                zk_market.deposit(token, amount_swapped);

                deposited += amount_swapped.into();
                accumulated += amount_swapped.into();
                i += 1;
            };
            let total_deposited = IERC20Dispatcher {
                contract_address: reserve_data.z_token_address
            }
                .balanceOf(get_contract_address());
            let total_borrowed = zk_market
                .get_user_debt_for_token(curr_contract_address, borrowing_token)
                .into();
            self
                .emit(
                    LiquidityLooped {
                        initial_amount: amount,
                        deposited: total_deposited,
                        token_deposit: token,
                        borrowed: total_borrowed,
                        token_borrowed: borrowing_token
                    }
                );

            self.deposits.append().write((token, total_deposited));
            self.borrows.append().write((borrowing_token, total_borrowed));
        }
    }

    #[abi(embed_v0)]
    impl Locker of ILocker<ContractState> {
        fn locked(ref self: ContractState, id: u32, data: Span<felt252>) -> Span<felt252> {
            let core = self.ekubo_core.read();
            let SwapData { pool_key, params, caller } =
                ekubo::components::shared_locker::consume_callback_data::<
                SwapData
            >(core, data);
            let delta = core.swap(pool_key, params);
            handle_delta(core, pool_key.token0, delta.amount0, caller);
            handle_delta(core, pool_key.token1, delta.amount1, caller);
            let swap_result = SwapResult { delta };

            let mut arr: Array<felt252> = ArrayTrait::new();
            Serde::serialize(@swap_result, ref arr);
            arr.span()
        }
    }
}
