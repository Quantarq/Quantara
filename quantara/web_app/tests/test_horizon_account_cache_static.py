from pathlib import Path


def test_get_account_data_uses_horizon_account_cache():
    source = Path("quantara/web_app/contract_tools/blockchain_call.py").read_text(encoding="utf-8")

    assert "cache_key = f\"horizon:account:" in source
    assert "get_cached_or_fetch(cache_key, ttl=5, fetch_fn=fetch_account)" in source
    assert "async def fetch_account()" in source