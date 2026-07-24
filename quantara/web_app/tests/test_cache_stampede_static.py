from pathlib import Path


CACHE_SOURCE = Path("quantara/web_app/contract_tools/cache.py").read_text()


def test_cache_miss_uses_setnx_refresh_claim():
    assert "claim_key = f\"{key}:refresh-lock\"" in CACHE_SOURCE
    assert "nx=True" in CACHE_SOURCE
    assert "ex=_REFRESH_CLAIM_SECONDS" in CACHE_SOURCE
    assert "_REFRESH_CLAIM_SECONDS = 5" in CACHE_SOURCE


def test_concurrent_miss_waits_for_claimer_before_fetching():
    assert "if not claimed:" in CACHE_SOURCE
    assert "refreshed = await _wait_for_refresh(client, key)" in CACHE_SOURCE
    assert "if refreshed is not None:" in CACHE_SOURCE
    assert "return refreshed" in CACHE_SOURCE
    assert "value = await fetch_fn()" in CACHE_SOURCE


def test_wait_loop_polls_cached_value_with_deadline():
    assert "deadline = asyncio.get_running_loop().time() + _REFRESH_CLAIM_SECONDS" in CACHE_SOURCE
    assert "await asyncio.sleep(_REFRESH_POLL_SECONDS)" in CACHE_SOURCE
    assert "cached = await _read_cached_value(client, key)" in CACHE_SOURCE