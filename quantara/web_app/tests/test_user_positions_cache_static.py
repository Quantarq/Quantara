"""Static coverage for user-position caching wiring."""

from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1] / "api"
CONTRACT_TOOLS_ROOT = Path(__file__).resolve().parents[1] / "contract_tools"
POSITION_SOURCE = (API_ROOT / "position.py").read_text(encoding="utf-8")
CACHE_SOURCE = (CONTRACT_TOOLS_ROOT / "cache.py").read_text(encoding="utf-8")


def test_user_positions_endpoint_uses_wallet_scoped_cache():
    assert "USER_POSITIONS_CACHE_TTL = 60" in POSITION_SOURCE
    assert "def _user_positions_cache_key(wallet_id: str, start: int, limit: int)" in POSITION_SOURCE
    assert 'return f"user_positions:{wallet_id}:{start}:{limit}"' in POSITION_SOURCE
    assert "await get_cached_or_fetch(" in POSITION_SOURCE
    assert "ttl=USER_POSITIONS_CACHE_TTL" in POSITION_SOURCE
    assert "fetch_fn=fetch_user_positions" in POSITION_SOURCE


def test_position_lifecycle_invalidates_user_positions_cache():
    assert "async def _invalidate_user_positions_cache" in POSITION_SOURCE
    assert 'await delete_cache_pattern(f"user_positions:{wallet_id}:*")' in POSITION_SOURCE
    assert "await _invalidate_user_positions_cache(form_data.wallet_id)" in POSITION_SOURCE
    assert "wallet_id = _get_wallet_id_for_position(position_id)" in POSITION_SOURCE
    assert "await _invalidate_user_positions_cache(wallet_id)" in POSITION_SOURCE
    assert "def _get_wallet_id_for_position_object(position: object | None)" in POSITION_SOURCE
    assert "getattr(position, \\"user_id\\", None)" in POSITION_SOURCE
    assert "_get_wallet_id_for_position_object(position)" in POSITION_SOURCE


def test_cache_helper_supports_pattern_invalidation():
    assert "async def delete_cache_pattern(pattern: str)" in CACHE_SOURCE
    assert "await client.scan(cursor=cursor, match=pattern, count=100)" in CACHE_SOURCE
    assert "await client.delete(*keys)" in CACHE_SOURCE
    assert "Cache invalidation failed" in CACHE_SOURCE