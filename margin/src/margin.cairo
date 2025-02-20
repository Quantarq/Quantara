#[starknet::contract]
pub mod Margin {
    use starknet::{
        event::EventEmitter,
        storage::{StoragePointerReadAccess, StoragePointerWriteAccess, StoragePathEntry, Map},
        ContractAddress, get_contract_address, get_caller_address, ClassHash,
    };
    use margin::{
        interface::IMargin,
        types::{Position, TokenAmount, PositionParameters}
    };
    

    #[storage]
    struct Storage {
       treasury_balances: Map<(ContractAddress, ContractAddress), TokenAmount>,
       pools: Map<ContractAddress, TokenAmount>,
       positions: Map<ContractAddress, Position>,
    }

    #[abi(embed_v0)]
    impl Margin of IMargin<ContractState>{
        fn deposit(ref self: ContractState, token: ContractAddress, amount: TokenAmount) {}
        fn withdraw(ref self: ContractState, token: ContractAddress, amount: TokenAmount) {}
        
        // TODO: Add Ekubo data for swap
        fn open_margin_position(ref self: ContractState, position_parameters: PositionParameters) {} 
        fn close_position(ref self: ContractState) {}
        fn liquidate(ref self: ContractState, user: ContractAddress) {}
    }
}
