#[starknet::contract]
mod Vault {
    use core::num::traits::Zero;
    use openzeppelin::access::ownable::OwnableComponent;
    use openzeppelin::token::erc20::interface::{IERC20Dispatcher, IERC20DispatcherTrait};
    use openzeppelin::upgrades::UpgradeableComponent;
    use openzeppelin::upgrades::interface::IUpgradeable;
    use spotnet::interfaces::{IVault, IDepositDispatcher};
    use spotnet::types::{TokenAmount};

    use starknet::ContractAddress;
    use starknet::storage::{
        StoragePointerReadAccess, StoragePointerWriteAccess, StoragePathEntry, Map
    };
    use starknet::{ClassHash, get_caller_address, get_contract_address};

    component!(path: OwnableComponent, storage: ownable, event: OwnableEvent);
    component!(path: UpgradeableComponent, storage: upgradeable, event: UpgradeableEvent);

    /// Ownable
    #[abi(embed_v0)]
    impl OwnableTwoStepMixinImpl =
        OwnableComponent::OwnableTwoStepMixinImpl<ContractState>;
    impl OwnableInternalImpl = OwnableComponent::InternalImpl<ContractState>;

    /// Upgradeable
    impl UpgradeableInternalImpl = UpgradeableComponent::InternalImpl<ContractState>;

    #[storage]
    struct Storage {
        token: ContractAddress,
        amounts: Map<ContractAddress, TokenAmount>,
        activeContracts: Map<ContractAddress, ContractAddress>,
        #[substorage(v0)]
        ownable: OwnableComponent::Storage,
        #[substorage(v0)]
        upgradeable: UpgradeableComponent::Storage
    }

    #[event]
    #[derive(Drop, starknet::Event)]
    enum Event {
        #[flat]
        OwnableEvent: OwnableComponent::Event,
        #[flat]
        UpgradeableEvent: UpgradeableComponent::Event,
        LiquidityAdded: LiquidityAdded,
        LiquidityWithdrawn: LiquidityWithdrawn,
        ContractAdded: ContractAdded
        PositionProtected: PositionProtected
    }

    #[derive(Drop, starknet::Event)]
    struct LiquidityAdded {
        #[key]
        user: ContractAddress,
        #[key]
        token: ContractAddress,
        amount: TokenAmount,
    }

    #[derive(Drop, starknet::Event)]
    struct LiquidityWithdrawn {
        #[key]
        user: ContractAddress,
        #[key]
        token: ContractAddress,
        amount: TokenAmount,
    }

    #[derive(Drop, starknet::Event)]
    struct ContractAdded {
        #[key]
        user: ContractAddress,
        #[key]
        deposit_contract: ContractAddress
    }

    #[derive(Drop, starknet::Event)]
    struct PositionProtected {
        #[key]
        token: ContractAddress,
        #[key]
        deposit_contract: ContractAddress,
        #[key]
        contract_owner: ContractAddress,
        amount: TokenAmount,
    }


    #[constructor]
    fn constructor(ref self: ContractState, owner: ContractAddress, token: ContractAddress) {
        assert(owner.is_non_zero(), 'Owner address is zero');
        self.ownable.initializer(owner);
        self.token.write(token);
    }

    #[abi(embed_v0)]
    impl UpgradeableImpl of IUpgradeable<ContractState> {
        fn upgrade(ref self: ContractState, new_class_hash: ClassHash) {
            // This function can only be called by the owner
            self.ownable.assert_only_owner();

            // Replace the class hash upgrading the contract
            self.upgradeable.upgrade(new_class_hash);
        }
    }


    #[abi(embed_v0)]
    impl VaultImpl of IVault<ContractState> {
        /// Stores liquidity in the vault by transferring tokens from the user.
        ///
        /// # Arguments
        ///
        /// * `amount` - The amount of tokens to deposit into the vault
        ///
        /// # Panics
        ///
        /// * When the user's token allowance for the vault is less than the deposit amount
        /// * When the user's token balance is less than the deposit amount
        ///
        /// # Events
        ///
        /// Emits a `LiquidityAdded` event with:
        /// * `user` - The address of the depositor
        /// * `token` - The address of the deposited token
        /// * `amount` - The amount of tokens deposited
        fn store_liquidity(ref self: ContractState, amount: TokenAmount) {
            let user = get_caller_address();
            let vault_contract = get_contract_address();
            let current_amount = self.amounts.entry(user).read();
    
            let token = self.token.read();
            let token_dispatcher = IERC20Dispatcher { contract_address: token };
            assert(
                token_dispatcher.allowance(user, vault_contract) >= amount,
                'Approved amount insufficient'
            );
            assert(token_dispatcher.balance_of(user) >= amount, 'Insufficient balance');
    
            // update new amount
            self.amounts.entry(user).write(current_amount + amount);
    
            // transfer token to vault
            token_dispatcher.transfer_from(user, vault_contract, amount);
    
            self.emit(LiquidityAdded { user, token, amount });
        }
    
        /// Withdraws liquidity from the vault by transferring tokens back to the user.
        ///
        /// # Arguments
        ///
        /// * `amount` - The amount of tokens to withdraw from the vault
        ///
        /// # Panics
        ///
        /// * When the user's deposited balance is less than the withdrawal amount
        ///
        /// # Events
        ///
        /// Emits a `LiquidityWithdrawn` event with:
        /// * `user` - The address of the withdrawer
        /// * `token` - The address of the withdrawn token
        /// * `amount` - The amount of tokens withdrawn
        fn withdraw_liquidity(ref self: ContractState, amount: TokenAmount) {
            let user = get_caller_address();
            let token = self.token.read();
            let current_amount = self.amounts.entry(user).read();
            assert(current_amount >= amount, 'Not enough tokens to withdraw');
    
            // update new amount
            self.amounts.entry(user).write(current_amount - amount);
    
            // transfer token to user
            IERC20Dispatcher { contract_address: token }.transfer(user, amount);
    
            self.emit(LiquidityWithdrawn { user, token, amount });
        }

        fn add_deposit_contract(ref self: ContractState, deposit_contract: ContractAddress){
            let user = get_caller_address();
            assert(deposit_contract.is_non_zero(), 'Deposit contract address is zero');
            self.activeContracts.entry(user).write(deposit_contract);
            self.emit(ContractAdded {user, deposit_contract});
        }

        fn protect_position(
            self: @TContractState, 
            deposit_contract: ContractAddress, 
            user: ContractAddress, 
            amount: TokenAmount
        ) {
            let token = self.token.read();
            let caller = get_caller_address();
            let vault_contract = get_contract_address();
            let vault_owner = self.ownable.Ownable_owner.read();
            let current_amount = self.amounts.entry(caller).read();

            assert(vault_owner == caller || user == caller, 'Caller must equal to vault owner or user');
            
            let token_dispatcher = IERC20Dispatcher { contract_address: token };
            assert(
                token_dispatcher.allowance(user, vault_contract) >= amount,
                'Approved amount insufficient'
            );
            assert(token_dispatcher.balance_of(user) >= amount, 'Insufficient balance');

            let deposit = IDepositDispatcher(deposit_contract);
            deposit.extra_deposit(token, amount);

            self.emit(
                PositionProtected {
                    token: token, 
                    deposit_contract: deposit_contract, 
                    contract_owner: user, 
                    amount: amount
                }
            )
        }
    }    
}
