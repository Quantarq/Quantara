from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEADERBOARD_API = ROOT / "api" / "leaderboard.py"
POSITION_CRUD = ROOT / "db" / "crud" / "position.py"
CACHE_HELPER = ROOT / "contract_tools" / "cache.py"


def test_leaderboard_endpoints_use_cache_keys_and_ttl():
    source = LEADERBOARD_API.read_text()

    assert "from web_app.contract_tools.cache import get_cached_or_fetch" in source
    assert "LEADERBOARD_CACHE_TTL_SECONDS = 30" in source
    assert "USER_LEADERBOARD_CACHE_KEY" in source
    assert "POSITION_TOKEN_STATISTICS_CACHE_KEY" in source
    assert "return await get_cached_or_fetch(" in source
    assert "leaderboard_db_connector.get_top_users_by_positions()" in source
    assert "leaderboard_db_connector.get_position_token_statistics()" in source


def test_position_lifecycle_invalidates_leaderboard_cache():
    source = POSITION_CRUD.read_text()

    assert "from web_app.contract_tools.cache import invalidate_leaderboard_cache" in source
    assert source.count("invalidate_leaderboard_cache()") >= 3
    assert "def close_position" in source
    assert "def open_position" in source
    assert "def liquidate_position" in source


def test_cache_helper_has_sync_pattern_invalidation():
    source = CACHE_HELPER.read_text()

    assert "import redis as redis_sync" in source
    assert "def delete_cache_pattern_sync(pattern: str) -> None:" in source
    assert "client.scan_iter(match=pattern)" in source
    assert "client.delete(*keys)" in source
    assert 'delete_cache_pattern_sync("leaderboard:*")' in source