import pytest
from httpx import AsyncClient
from web_app.api.main import app
from web_app.api.middleware import SecurityHeadersMiddleware


def test_security_headers_registered():
    middleware_classes = [m.cls for m in app.user_middleware]
    assert SecurityHeadersMiddleware in middleware_classes


@pytest.mark.asyncio
async def test_security_headers_present():
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "content-security-policy" in response.headers
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


@pytest.mark.asyncio
async def test_hsts_not_set_when_not_production(monkeypatch):
    monkeypatch.setenv("ENV_VERSION", "DEV")
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/health")
    assert "strict-transport-security" not in response.headers


@pytest.mark.asyncio
async def test_hsts_set_in_production(monkeypatch):
    monkeypatch.setenv("ENV_VERSION", "PROD")
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/health")
    assert "strict-transport-security" in response.headers
    hsts = response.headers["strict-transport-security"]
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts
