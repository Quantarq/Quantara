"""Static coverage for split liveness/readiness routes."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN_SOURCE = (ROOT / "web_app" / "api" / "main.py").read_text(encoding="utf-8")
COMPOSE_SOURCE = (ROOT.parent / "devops" / "docker-compose.quantara.yaml").read_text(
    encoding="utf-8"
)


def test_liveness_and_compatibility_routes_are_separate_from_readiness():
    assert '@app.get("/livez"' in MAIN_SOURCE
    assert '@app.get("/health"' in MAIN_SOURCE
    assert 'return {"status": "healthy", "database": "up", "redis": "up"}' in MAIN_SOURCE
    assert '@app.get("/readyz"' in MAIN_SOURCE
    assert 'response.status_code = 503' in MAIN_SOURCE


def test_readiness_checks_database_redis_and_soroban_rpc():
    assert "async def _check_database" in MAIN_SOURCE
    assert "async def _check_redis" in MAIN_SOURCE
    assert "async def _check_soroban_rpc" in MAIN_SOURCE
    assert 'text("SELECT 1")' in MAIN_SOURCE
    assert "client.ping()" in MAIN_SOURCE
    assert 'os.getenv("STELLAR_SOROBAN_RPC_URL")' in MAIN_SOURCE
    assert '"method": "getHealth"' in MAIN_SOURCE


def test_backend_healthcheck_uses_readiness_endpoint():
    assert "http://localhost:8000/readyz" in COMPOSE_SOURCE
    assert "http://localhost:8000/health" not in COMPOSE_SOURCE