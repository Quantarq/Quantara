from pathlib import Path
import unittest


API_ROOT = Path(__file__).resolve().parents[1] / "api"
CRUD_ROOT = Path(__file__).resolve().parents[1] / "db" / "crud"
TASK_ROOT = Path(__file__).resolve().parents[1] / "tasks"
CACHE_ROOT = Path(__file__).resolve().parents[1] / "contract_tools"


class GetStatsSqlCacheStaticTests(unittest.TestCase):
    def test_get_stats_uses_cached_sql_usdc_aggregate(self):
        source = (API_ROOT / "user.py").read_text()

        self.assertIn("GET_STATS_CACHE_TTL_SECONDS = 10", source)
        self.assertIn("get_cached_or_fetch", source)
        self.assertIn("GET_STATS_CACHE_KEY", source)
        self.assertIn("get_total_opened_amount_usdc", source)
        self.assertNotIn("get_total_amounts_for_open_positions()", source)

    def test_position_connector_pushes_usdc_total_into_sql(self):
        source = (CRUD_ROOT / "position.py").read_text()

        self.assertIn("def get_total_opened_amount_usdc", source)
        self.assertIn("WITH token_prices(token_symbol, usdc_price) AS", source)
        self.assertIn('FROM "position" p', source)
        self.assertIn("SUM(CAST(p.amount AS NUMERIC) * token_prices.usdc_price)", source)
        self.assertIn("WHERE p.status = :opened_status", source)
        self.assertIn("Status.OPENED.value", source)

    def test_opened_and_closed_lifecycles_invalidate_stats_cache(self):
        position_api = (API_ROOT / "position.py").read_text()
        outbox_task = (TASK_ROOT / "outbox_relay.py").read_text()
        cache_source = (CACHE_ROOT / "cache.py").read_text()

        self.assertIn("async def delete_cache_key", cache_source)
        self.assertIn("await delete_cache_key(GET_STATS_CACHE_KEY)", position_api)
        self.assertIn("asyncio.run(delete_cache_key(GET_STATS_CACHE_KEY))", outbox_task)


if __name__ == "__main__":
    unittest.main()
