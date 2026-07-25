from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LEADERBOARD_API = ROOT / "api" / "leaderboard.py"
POSITION_CRUD = ROOT / "db" / "crud" / "position.py"
CACHE_HELPER = ROOT / "contract_tools" / "cache.py"


class LeaderboardCacheStaticTests(unittest.TestCase):
    def test_leaderboard_endpoints_use_cache_names_and_ttl(self):
        source = LEADERBOARD_API.read_text()

        self.assertIn(
            "from web_app.contract_tools.cache import get_cached_or_fetch",
            source,
        )
        self.assertIn("LEADERBOARD_CACHE_TTL_SECONDS = 30", source)
        self.assertIn("USER_LEADERBOARD_CACHE_NAME", source)
        self.assertIn("POSITION_TOKEN_STATISTICS_CACHE_NAME", source)
        self.assertIn(
            '":".join(("leaderboard", "user", "top_positions"))',
            source,
        )
        self.assertIn(
            '("leaderboard", "position_tokens", "statistics")',
            source,
        )
        self.assertIn("return await get_cached_or_fetch(", source)
        self.assertIn(
            "leaderboard_db_connector.get_top_users_by_positions()",
            source,
        )
        self.assertIn(
            "leaderboard_db_connector.get_position_token_statistics()",
            source,
        )

    def test_position_lifecycle_invalidates_leaderboard_cache(self):
        source = POSITION_CRUD.read_text()

        self.assertIn(
            "from web_app.contract_tools.cache import invalidate_leaderboard_cache",
            source,
        )
        self.assertGreaterEqual(source.count("invalidate_leaderboard_cache()"), 3)
        self.assertIn("def close_position", source)
        self.assertIn("def open_position", source)
        self.assertIn("def liquidate_position", source)

    def test_cache_helper_has_sync_pattern_invalidation(self):
        source = CACHE_HELPER.read_text()

        self.assertIn("import redis as redis_sync", source)
        self.assertIn("def delete_cache_pattern_sync(pattern: str) -> None:", source)
        self.assertIn("client.scan_iter(match=pattern)", source)
        self.assertIn("client.delete(*keys)", source)
        self.assertIn('delete_cache_pattern_sync("leaderboard:*")', source)


if __name__ == "__main__":
    unittest.main()
