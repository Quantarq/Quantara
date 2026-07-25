import importlib
from unittest.mock import MagicMock, patch


def test_production_disables_in_memory_rate_limit_fallback():
    with patch.dict("os.environ", {"ENV_VERSION": "PROD", "REDIS_URL": "redis://redis:6379"}):
        import web_app.api.rate_limiter as rate_limiter

        importlib.reload(rate_limiter)

        assert rate_limiter.allow_in_memory_fallback() is False
        assert rate_limiter.limiter._in_memory_fallback_enabled is False


def test_development_keeps_in_memory_rate_limit_fallback():
    with patch.dict("os.environ", {"ENV_VERSION": "DEV", "REDIS_URL": "redis://127.0.0.1:1"}):
        import web_app.api.rate_limiter as rate_limiter

        importlib.reload(rate_limiter)

        assert rate_limiter.allow_in_memory_fallback() is True
        assert rate_limiter.limiter._in_memory_fallback_enabled is True


def test_production_startup_pings_redis_backend():
    with patch.dict("os.environ", {"ENV_VERSION": "PROD", "REDIS_URL": "redis://redis:6379"}):
        import web_app.api.rate_limiter as rate_limiter

        importlib.reload(rate_limiter)
        fake_client = MagicMock()
        with patch.object(rate_limiter.redis.Redis, "from_url", return_value=fake_client) as from_url:
            rate_limiter.assert_rate_limiter_backend_available()

    from_url.assert_called_once()
    fake_client.ping.assert_called_once()
    fake_client.close.assert_called_once()


def test_development_startup_skips_redis_ping():
    with patch.dict("os.environ", {"ENV_VERSION": "DEV", "REDIS_URL": "redis://127.0.0.1:1"}):
        import web_app.api.rate_limiter as rate_limiter

        importlib.reload(rate_limiter)
        with patch.object(rate_limiter.redis.Redis, "from_url") as from_url:
            rate_limiter.assert_rate_limiter_backend_available()

    from_url.assert_not_called()