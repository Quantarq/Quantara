import importlib
import unittest
from unittest.mock import MagicMock, patch


class RateLimiterProductionFallbackTests(unittest.TestCase):
    def test_production_disables_in_memory_rate_limit_fallback(self):
        with patch.dict(
            "os.environ",
            {"ENV_VERSION": "PROD", "REDIS_URL": "redis://redis:6379"},
        ):
            import web_app.api.rate_limiter as rate_limiter

            importlib.reload(rate_limiter)

            self.assertFalse(rate_limiter.allow_in_memory_fallback())
            self.assertFalse(rate_limiter.limiter._in_memory_fallback_enabled)

    def test_development_keeps_in_memory_rate_limit_fallback(self):
        with patch.dict(
            "os.environ",
            {"ENV_VERSION": "DEV", "REDIS_URL": "redis://127.0.0.1:1"},
        ):
            import web_app.api.rate_limiter as rate_limiter

            importlib.reload(rate_limiter)

            self.assertTrue(rate_limiter.allow_in_memory_fallback())
            self.assertTrue(rate_limiter.limiter._in_memory_fallback_enabled)

    def test_production_startup_pings_redis_backend(self):
        with patch.dict(
            "os.environ",
            {"ENV_VERSION": "PROD", "REDIS_URL": "redis://redis:6379"},
        ):
            import web_app.api.rate_limiter as rate_limiter

            importlib.reload(rate_limiter)
            fake_client = MagicMock()
            with patch.object(
                rate_limiter.redis.Redis,
                "from_url",
                return_value=fake_client,
            ) as from_url:
                rate_limiter.assert_rate_limiter_backend_available()

        from_url.assert_called_once()
        fake_client.ping.assert_called_once()
        fake_client.close.assert_called_once()

    def test_development_startup_skips_redis_ping(self):
        with patch.dict(
            "os.environ",
            {"ENV_VERSION": "DEV", "REDIS_URL": "redis://127.0.0.1:1"},
        ):
            import web_app.api.rate_limiter as rate_limiter

            importlib.reload(rate_limiter)
            with patch.object(rate_limiter.redis.Redis, "from_url") as from_url:
                rate_limiter.assert_rate_limiter_backend_available()

        from_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
