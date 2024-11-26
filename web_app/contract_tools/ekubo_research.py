"""
Ekubo Flash Loan Research and Implementation Guide
================================================

This research document outlines how to implement flash loans on Ekubo AMM platform,
based on their documentation and implementation examples.

Key Concepts:
------------
1. Flash Accounting: Ekubo's internal token balance accounting system.
2. Free Flash Loans: No fees for borrowing within same transaction.
3. Atomic Execution: All operations must complete in single transaction.

Contract References:
------------------
1. Ekubo Core (Sepolia): 
   0x0444a09d96389aa7148f1aada508e30b71299ffe650d9c97fdaae38cb9a23384

2. Ekubo Router (Sepolia):
   0x0045f933adf0607292468ad1c1dedaa74d5ad166392590e72676a34d01d7b763

Documentation: https://docs.ekubo.org/


Implementation Flow:
------------------
API Endpoints(https://mainnet-api.ekubo.org/openapi.json) and Data Structures
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import httpx
from pydantic import BaseModel

@dataclass
class PoolKey:
    """Ekubo pool identification structure"""
    token0: str
    token1: str
    fee: int
    tick_spacing: int
    extension: str

@dataclass
class SwapRoute:
    """Structure for defining swap path"""
    pool_key: PoolKey #Dict[str, str] - Contains token0, token1, fee, tick_spacing, extension
    sqrt_ratio_limit: int
    skip_ahead: int

@dataclass
class TokenAmount:
    """Token amount with direction"""
    token: str
    amount: int
    is_positive: bool

class RouteQuote(BaseModel):
    """Single route quote from API"""
    amount: str
    priceImpact: str
    route: List[Dict]

class QuoteResponse(BaseModel):
    """Full API response structure"""
    specifiedAmount: str
    routes: List[RouteQuote]

class EkuboFlashLoan:
    """
    Main class for handling Ekubo Flash Loan operations
    
    Key Features:
    - No upfront fees required
    - Must repay within same transaction
    - Uses flash accounting for internal balance management
    """

    def __init__(self, core_contract:str):
        # Core contract - handles actual swaps and flash accounting
        self.core_contract = core_contract
        self.api_url = "https://mainnet-api.ekubo.org"

    async def get_profitable_route(self, input_token: str, amount: int,
                                   min_profit_bps: int = 50
                                   ) -> Optional[Tuple[List[SwapRoute], int]]:
        """
        Find profitable arbitrage route using Ekubo API
        
        Example API call:
        GET https://mainnet-api.ekubo.org/quote/{amount}/{input_token}/{input_token}

        Args: 
        - input_token: Token address
        - amount: Amount in token decimals
        - min_profit_bps: Minimum profit required in basis points
        
        Returns:
            Tuple of (route, expected_output_amount) if profitable route found,
            None otherwise
        """

        # Convert amount to integer, handling any number of decimals
        # decimal_places = 18  # Default decimal places for most tokens
        # amount_int = int(amount * Decimal(10**decimal_places))

        try:
            async with httpx.AsyncClient() as client:
                # Get quote for potential arbitrage route
                response = await client.get(
                    f"{self.api_url}/quote/{amount}/{input_token}/{input_token}"
                )
                response.raise_for_status()

                quote_data = QuoteResponse.model_validate(response.json())
                return self._find_best_route(quote_data, amount, min_profit_bps)

        except (httpx.RequestError, ValueError) as e:
            print(f"Error getting quote: {e}")
            return None

    def _find_best_route(self, quote_data: QuoteResponse, input_amount: int,
                         min_profit_bps: int) -> Optional[Tuple[List[SwapRoute], int]]:
        """
        Select most profitable route from quote response
        """
        best_profit = 0
        best_route = None
        best_output = 0

        for route_quote in quote_data.routes:
            output_amount = int(route_quote.amount)
            profit_bps = (output_amount - input_amount) * 10000 // input_amount

            # Consider price impact (converted from percentage to bps)
            price_impact_bps = int(Decimal(route_quote.priceImpact) * 100)
            effective_profit_bps = profit_bps - abs(price_impact_bps)

            if effective_profit_bps > best_profit and effective_profit_bps >= min_profit_bps:
                best_profit = effective_profit_bps
                best_route = [self._parse_route_node(node) for node in route_quote.route]
                best_output = output_amount

        if best_route:
            return best_route, best_output
        return None

    def _parse_route_node(self, node: Dict) -> SwapRoute:
        """Parse single route node from API response"""
        return SwapRoute(
            pool_key=PoolKey(
                token0=node['pool_key']['token0'],
                token1=node['pool_key']['token1'],
                fee=int(node['pool_key']['fee'], 16),
                tick_spacing=node['pool_key']['tick_spacing'],
                extension=node['pool_key']['extension']
            ),
            sqrt_ratio_limit=int(node['sqrt_ratio_limit'], 16),
            skip_ahead=int(node['skip_ahead'], 16)
        )

    def prepare_flash_loan_tx(self, route: List[SwapRoute],
            borrow_amount: TokenAmount) -> Dict:
        """
        Prepare transaction for flash loan arbitrage
            
        Transaction flow:
        1. Borrow tokens via flash accounting (no explicit borrow call needed)
        2. Execute swaps through provided route
        3. Verify profit
        4. Repay loan automatically from swap proceeds
        """
        return {
                'contract_address': self.core_contract,
                'entry_point_selector': 'multi_route_swap',
                'calldata': self._encode_multi_route_swap(route, borrow_amount)
            }

    def _encode_multi_route_swap(self, route: List[SwapRoute],
            token_amount: TokenAmount) -> List[int]:
        """Encode parameters for multihop_swap"""
        calldata = [len(route)]  # Route length

            # Encode route
        for node in route:
            calldata.extend([
                int(node.pool_key.token0, 16),
                int(node.pool_key.token1, 16),
                node.pool_key.fee,
                node.pool_key.tick_spacing,
                int(node.pool_key.extension, 16),
                node.sqrt_ratio_limit,
                node.skip_ahead
                ])

            # Encode amount
        calldata.extend([
            int(token_amount.token, 16),
            token_amount.amount
        ])

        return calldata





# get_transaction_data rework
async def get_transaction_data(deposit_token: str, scaled_amount: int,) -> Optional[dict]:
    """
    Modified version using flash loans
    
    Flow:
    1. Calculate profitable route
    2. Prepare flash loan transaction
    3. Return transaction data
    """
    # Initialize flash loan handler
    ekubo = EkuboFlashLoan(
        core_contract="0x0444a09d96389aa7148f1aada508e30b71299ffe650d9c97fdaae38cb9a23384"
    )

    # Find profitable route
    route_result = await ekubo.get_profitable_route(
        input_token=deposit_token,
        amount=scaled_amount,
        min_profit_bps=50  # Minimum 0.5% profit
    )

    if not route_result:
        return None

    route, _output_amount = route_result

    # Prepare borrow amount
    borrow_amount = TokenAmount(
        token=deposit_token,
        amount=scaled_amount,
        is_positive=True
    )

    return ekubo.prepare_flash_loan_tx(route, borrow_amount)
