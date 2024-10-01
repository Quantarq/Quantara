#[starknet::contract]
pub mod Core {
    use core::num::traits::Zero;

    use spotnet::constants::{EKUBO_CORE_MAINNET, ZKLEND_MARKET, USER_CONTRACT_HASH};

    use spotnet::interfaces::{ICore};

    use starknet::storage::{Map, StorageMapWriteAccess, StorageMapReadAccess};
    use starknet::syscalls::deploy_syscall;
    use starknet::{ContractAddress};
    use starknet::{get_caller_address};

    #[storage]
    struct Storage {
        user_contracts: Map<ContractAddress, ContractAddress>
    }

    #[constructor]
    fn constructor(ref self: ContractState) {}

    #[abi(embed_v0)]
    impl CoreImpl of ICore<ContractState> {
        fn deploy_user_contract(ref self: ContractState) -> ContractAddress {
            let caller = get_caller_address();
            assert(self.user_contracts.read(caller).is_zero(), 'Contract already exists');
            let res = deploy_syscall(
                USER_CONTRACT_HASH.try_into().unwrap(),
                caller.into(),
                array![EKUBO_CORE_MAINNET, ZKLEND_MARKET].span(),
                false
            );
            let (address, _) = res.expect('Could not deploy your contract');
            self.user_contracts.write(caller, address);
            address
        }

        fn get_users_account(self: @ContractState, address: ContractAddress) -> ContractAddress {
            self.user_contracts.read(address)
        }
    }
}
