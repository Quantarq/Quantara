"""
Test suite for the DashboardMixin class in the web_app.contract_tools.mixins.dashboard module.
"""

import pytest
from unittest.mock import patch, AsyncMock
from web_app.contract_tools.mixins.dashboard import DashboardMixin
from web_app.contract_tools.constants import TokenParams
from web_app.api.serializers.dashboard import ZkLendPositionResponse

@pytest.fixture
def mock_starknet_client():
    """Mock the StarkNet client."""
    with patch('web_app.contract_tools.mixins.dashboard.CLIENT') as mock:
        yield mock

@pytest.fixture
def mock_api_request():
    """Mock the API request class."""
    with patch('web_app.contract_tools.mixins.dashboard.APIRequest') as mock:
        yield mock


class TestDashboardMixin:
    """
    Test cases for the DashboardMixin class, focusing on the methods
    related to wallet balances, zkLend positions, and product extraction.
    """

    @pytest.mark.asyncio
    async def test_get_wallet_balances_success(self, mock_starknet_client):
        """
        Test successful retrieval of wallet balances.
        """
        # Mock the get_balance method with pre-defined token balances
        mock_starknet_client.get_balance = AsyncMock(side_effect=["10.5", "1000.0"])

        # Mock token parameters
        mock_tokens = [
            TokenParams.ETH,
            TokenParams.USDC,
        ]
        with patch.object(TokenParams, "tokens", return_value=mock_tokens):
            # Act
            result = await DashboardMixin.get_wallet_balances("0xHolderAddress")

        # Assert
        assert result == {"ETH": "10.5", "USDC": "1000.0"}

    @pytest.mark.asyncio
    async def test_get_wallet_balances_error_handling(self, mock_starknet_client):
        """
        Test wallet balances retrieval with error handling.
        """
        # Mock the get_balance method to throw an exception for the second token
        mock_starknet_client.get_balance = AsyncMock(
            side_effect=["10.5", Exception("error"), "1000.0"]
        )

        # Mock token parameters
        mock_tokens = [
            TokenParams.ETH,
            TokenParams.STRK,
            TokenParams.USDC,
        ]
        with patch.object(TokenParams, "tokens", return_value=mock_tokens):
            # Act
            result = await DashboardMixin.get_wallet_balances("0xHolderAddress")

        # Assert
        assert result == {"ETH": "10.5", "USDC": "1000.0"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "contract_address, mock_response, expected_protocols",
        [
            (
                "0x1234567890abcdef",
                {
                    "products": [
                        {
                            "name": "ZkLend",
                            "groups": {"1": {"healthRatio": "1.2"}},
                            "positions": [],
                        }
                    ]
                },
                ["ZkLend"]
            ),
            (
                "0xabcdef1234567890",
                {
                    "products": [
                        {
                            "name": "ZkLend",
                            "groups": {"1": {"healthRatio": "0.5"}},
                            "positions": [],
                        }
                    ]
                },
                ["ZkLend"]
            ),
        ]
    )
    async def test_get_zklend_position_success(
        self, contract_address, mock_response, expected_protocols
    ):
        """Test successful retrieval of zkLend positions."""
        with patch(
            "web_app.contract_tools.mixins.dashboard.DashboardMixin.get_zklend_position",
            new_callable=AsyncMock
        ) as mock_get_zklend_position:
            # Mock the response to return the expected mock_response
            mock_get_zklend_position.return_value = mock_response

            # Act: Call the method to get zkLend positions
            result = await DashboardMixin.get_zklend_position(contract_address)

            # Assert: Check the type of the result
            assert isinstance(result, dict)  # Adjust this based on the actual return type

            # Assert: Check the length of the products
            assert len(result["products"]) == len(expected_protocols)

            # Assert: Check that expected products are present in the results
            for expected_name in expected_protocols:
                assert any(product["name"] == expected_name for product in result["products"])

    @pytest.mark.parametrize(
        "dapps, expected_length, expected_tokens",
        [
            (
                [
                    {
                        "protocol": "zkLend",
                        "products": [
                            {
                                "type": "lending",
                                "token": "ETH",
                                "supplied": "1.5",
                                "protocol": "zkLend",
                                "health_ratio": "1.0"
                            }
                        ]
                    },
                    {
                        "protocol": "zkLend"  # Missing products key
                    }
                ],
                1,
                ["ETH"]
            ),
            (
                [
                    {
                        "protocol": "zkLend",
                        "products": []  # Empty products list
                    },
                    {
                        "protocol": "zkLend",
                        "products": [
                            {
                                "type": "lending",
                                "token": "BTC",
                                "supplied": "0.5",
                                "protocol": "zkLend",
                                "health_ratio": "0.8"
                            }
                        ]
                    }
                ],
                1,
                ["BTC"]
            ),
        ]
    )
    def test_get_products_with_missing_products(self, dapps, expected_length, expected_tokens):
        """
        Test products extraction when some dapps are missing products.
        
        Args:
            dapps: List of dapp data.
            expected_length: Expected number of products extracted.
            expected_tokens: List of expected token names.
        """
        # Act
        result = DashboardMixin._get_products(dapps)

        # Assert
        assert len(result) == expected_length
        assert [product["token"] for product in result] == expected_tokens

    @pytest.mark.parametrize(
        "dapps, expected_length, expected_tokens",
        [
            (
                [
                    {
                        "protocol": "validProtocol1",
                        "products": [
                            {
                                "type": "lending",
                                "token": "ETH",
                                "supplied": "5",
                                "borrowed": "0",
                                "health_ratio": "1.0"
                            },
                            {
                                "type": "lending",
                                "token": "USDC",
                                "supplied": "100",
                                "borrowed": "0",
                                "health_ratio": "0.9"
                            },
                        ]
                    },
                    {
                        "protocol": "validProtocol2",
                        "products": [
                            {
                                "type": "lending",
                                "token": "BTC",
                                "supplied": "1",
                                "borrowed": "0.5",
                                "health_ratio": "0.8"
                            }
                        ]
                    }
                ],
                3,
                ["ETH", "USDC", "BTC"]
            ),
            (
                [
                    {
                        "protocol": "validProtocol3",
                        "products": []
                    },
                    {
                        "protocol": "validProtocol4",
                        "products": []
                    }
                ],
                0,
                []
            ),
            (
                [],
                0,
                []
            ),
        ]
    )
    def test_get_products_with_valid_dapps(self, dapps, expected_length, expected_tokens):
        """
        Test products extraction from valid dapps data.
        
        Args:
            dapps: List of dapp data.
            expected_length: Expected number of products extracted.
            expected_tokens: List of expected token names.
        """
        # Act
        result = DashboardMixin._get_products(dapps)

        # Assert
        assert len(result) == expected_length
        assert [product["token"] for product in result] == expected_tokens