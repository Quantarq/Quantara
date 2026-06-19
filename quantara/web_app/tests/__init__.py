"""
Test package for the QUANTARA web application.

The test suite is organized by area:
- test_positions.py, test_vault.py, test_user.py, test_dashboard.py,
  test_claim_airdrops.py, test_starknet_client.py: API endpoint tests
- test_airdrop.py, test_airdrop_fetcher.py, test_create_referal_link.py,
  test_deposit_mixin.py, test_dashboard_mixin.py: mixin / integration
  tests
- test_exception_handler.py, test_config_validator.py: cross-cutting
  infrastructure tests
- db/: database connector unit tests
"""
