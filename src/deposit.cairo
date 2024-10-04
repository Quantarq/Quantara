#[starknet::contract]
mod Deposit {
    use alexandria_math::fast_power::fast_power;
    use ekubo::components::shared_locker::handle_delta;
    use ekubo::interfaces::core::SwapParameters;
    use ekubo::interfaces::core::{ICoreDispatcher, ICoreDispatcherTrait, ILocker};
    use ekubo::types::i129::i129;
    use ekubo::types::keys::PoolKey;
    use spotnet::constants::ZK_PERCENTS_DECIMALS;
    use spotnet::interfaces::IDeposit;

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

    use openzeppelin::access::ownable::OwnableComponent;
    
    component!(path: OwnableComponent, storage: ownable, event: OwnableEvent);

    #[abi(embed_v0)]
    impl OwnableMixinImpl = OwnableComponent::OwnableMixinImpl<ContractState>;
    impl OwnableInternalImpl = OwnableComponent::InternalImpl<ContractState>;

    #[storage]
    struct Storage {
        ekubo_core: ICoreDispatcher,
        zk_market: IMarketDispatcher,
        deposits: Vec<(ContractAddress, u256)>,
        borrows: Vec<(ContractAddress, u256)>,

        #[substorage(v0)]
        ownable: OwnableComponent::Storage
    }

    #[constructor]
    fn constructor(
        ref self: ContractState, owner: ContractAddress, ekubo_core: ICoreDispatcher, zk_market: IMarketDispatcher
    ) {
        self.ownable.initializer(owner);
        self.ekubo_core.write(ekubo_core);
        self.zk_market.write(zk_market);
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
    
    fn get_withdraw_amount(
        total_deposited: u256, total_debt: u256, collateral_factor: u256, supply_token_price: u256, debt_token_price: u256, supply_decimals: u256, debt_decimals: u256
    ) -> u256 {
        let deposited = total_deposited * supply_token_price / supply_decimals;
        let free_amount = (deposited * collateral_factor / ZK_PERCENTS_DECIMALS) - total_debt.into();
        let withdraw_amount = free_amount * debt_token_price / debt_decimals;
        withdraw_amount
    }

    #[derive(starknet::Event, Drop)]
    struct LiquidityLooped {
        initial_amount: u256,
        deposited: u256,
        token_deposit: ContractAddress,
        borrowed: u256,
        token_borrowed: ContractAddress
    }

    #[derive(starknet::Event, Drop)]
    struct PositionClosed {
        deposit_token: ContractAddress,
        debt_token: ContractAddress,
        initial_deposit: u256,
        withdrawn_amount: u256,
        repaid_amount: u256
    }

    #[event]
    #[derive(Drop, starknet::Event)]
    enum Event {
        LiquidityLooped: LiquidityLooped,
        PositionClosed: PositionClosed,
        #[flat]
        OwnableEvent: OwnableComponent::Event
    }

    #[abi(embed_v0)]
    impl Deposit of IDeposit<ContractState> {
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
            // TODO: Add borrow factor in calculation to support more tokens
            self.ownable.assert_only_owner();
            let DepositData { token, amount, multiplier } = deposit_data;
            assert(multiplier < 5, 'Not supported');
            let (EKUBO_LOWER_SQRT_LIMIT, EKUBO_UPPER_SQRT_LIMIT) = (
                18446748437148339061, 6277100250585753475930931601400621808602321654880405518632
            );
            let token_dispatcher = IERC20Dispatcher { contract_address: token };
            let zk_market = self.zk_market.read();
            let is_token1 = token == pool_key.token0;
            let (borrowing_token, sqrt_limit) = if is_token1 {
                (pool_key.token1, EKUBO_UPPER_SQRT_LIMIT)
            } else {
                (pool_key.token0, EKUBO_LOWER_SQRT_LIMIT)
            };
            let curr_contract_address = get_contract_address();

            token_dispatcher.transferFrom(caller, curr_contract_address, amount);
            let reserve_data = zk_market.get_reserve_data(token);

            let collateral_factor: u256 = reserve_data.collateral_factor.into();

            zk_market.enable_collateral(token);

            let deposit_token_decimals = fast_power(
                10, token_dispatcher.decimals().try_into().unwrap()
            );
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

        fn close_position(ref self: ContractState, supply_token: ContractAddress, debt_token: ContractAddress, pool_key: PoolKey, supply_price: u256, debt_price: u256) {
            // TODO: Remove prices when Oracle is integrated.
            // TODO: Add assertions
            let token_disp = IERC20Dispatcher { contract_address: supply_token };
            let zk_market = self.zk_market.read();
            let reserve_data = zk_market.get_reserve_data(supply_token);
            let z_token_disp = IERC20Dispatcher {contract_address: reserve_data.z_token_address};
            let contract_address = get_contract_address();
            let initial_deposit = z_token_disp.balanceOf(contract_address);
            let mut debt = zk_market.get_user_debt_for_token(
                contract_address, debt_token
            );

            let debt_dispatcher = IERC20Dispatcher {contract_address: debt_token};
            let (supply_decimals, debt_decimals) = (
                fast_power(10, token_disp.decimals().into()),
                fast_power(10, debt_dispatcher.decimals().into())
            );
            let (SQRT_LIMIT_REPAY, SQRT_LIMIT_WITHDRAW) = if supply_token == pool_key.token0 {
                (18446748437148339061, 6277100250585753475930931601400621808602321654880405518632)
            } else {
                (6277100250585753475930931601400621808602321654880405518632, 18446748437148339061)
            };
            let is_token1_repay_swap = supply_token == pool_key.token1;
            let mut repaid_amount: u256 = 0;
            while debt != 0 {
                let withdraw_amount = get_withdraw_amount(
                    z_token_disp.balanceOf(contract_address),
                    debt.into(),
                    reserve_data.collateral_factor.into(),
                    supply_price,
                    debt_price,
                    supply_decimals,
                    debt_decimals
                );
                zk_market.withdraw(supply_token, withdraw_amount.try_into().unwrap());

                let params = SwapParameters {
                    amount: i129 { mag: withdraw_amount.try_into().unwrap(), sign: false },
                    is_token1: is_token1_repay_swap,
                    sqrt_ratio_limit: SQRT_LIMIT_REPAY,
                    skip_ahead: 0
                };
                let delta = self.swap(SwapData {params, pool_key, caller: contract_address}).delta;
                let amount_swapped: u256 = if is_token1_repay_swap {delta.amount0.mag.into()} else {delta.amount1.mag.into()};
                
                if debt.into() > amount_swapped {
                    repaid_amount += amount_swapped;
                    debt_dispatcher.approve(zk_market.contract_address, amount_swapped.into());
                    zk_market.repay(debt_token, amount_swapped.try_into().unwrap());
                } else {
                    repaid_amount += debt.into();
                    debt_dispatcher.approve(zk_market.contract_address, debt.into());
                    zk_market.repay_all(debt_token);
                }

                debt = zk_market.get_user_debt_for_token(
                    contract_address, debt_token
                );
            };
            
            let left = debt_dispatcher.balanceOf(contract_address);
            let params = SwapParameters {
                amount: i129 { mag: left.try_into().unwrap(), sign: false },
                is_token1: !is_token1_repay_swap,
                sqrt_ratio_limit: SQRT_LIMIT_WITHDRAW,
                skip_ahead: 0
            };
            self.swap(SwapData {params, pool_key, caller: contract_address});
            zk_market.withdraw_all(supply_token);
            zk_market.disable_collateral(supply_token);
            self.emit(PositionClosed {
                deposit_token: supply_token, debt_token, initial_deposit, repaid_amount, withdrawn_amount: token_disp.balanceOf(contract_address)
            });
            // FIXME: Add aggregation of withdraws.
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
