
import asyncio
from decimal import Decimal
from quantara.soroban.adapters import LendingAdapterFactory


async def main():
    print("Testing Blend Lending Adapter...")
    
    # Create adapter
    adapter = LendingAdapterFactory.create("blend")
    print("Adapter created successfully!")
    
    # Test get_all_reserves
    print("\nTesting get_all_reserves...")
    reserves = await adapter.get_all_reserves()
    for reserve in reserves:
        print(f"  - {reserve.token_symbol}: Supply APY {reserve.supply_apy*100}%, Borrow APY {reserve.borrow_apy*100}%")
    
    # Test get_reserve_data
    print("\nTesting get_reserve_data for XLM...")
    xlm_reserve = await adapter.get_reserve_data("XLM")
    print(f"  XLM reserve: {xlm_reserve}")
    
    # Test get_user_position
    print("\nTesting get_user_position...")
    user_pos = await adapter.get_user_position("GABCDEF123456", "XLM")
    print(f"  User position: {user_pos}")
    
    # Test deposit
    print("\nTesting deposit...")
    tx_hash = await adapter.deposit("GABCDEF123456", "XLM", Decimal("100"))
    print(f"  Deposit tx hash: {tx_hash}")
    
    # Test borrow
    print("\nTesting borrow...")
    borrow_tx = await adapter.borrow("GABCDEF123456", "USDC", Decimal("50"))
    print(f"  Borrow tx hash: {borrow_tx}")
    
    # Test repay
    print("\nTesting repay...")
    repay_tx = await adapter.repay("GABCDEF123456", "USDC", Decimal("50"))
    print(f"  Repay tx hash: {repay_tx}")
    
    # Test withdraw
    print("\nTesting withdraw...")
    withdraw_tx = await adapter.withdraw("GABCDEF123456", "XLM", Decimal("100"))
    print(f"  Withdraw tx hash: {withdraw_tx}")
    
    print("\nAll tests passed!")
    
    await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
