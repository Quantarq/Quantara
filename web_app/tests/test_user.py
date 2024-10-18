import httpx
import pytest


@pytest.fixture(scope="function")
async def async_client():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        yield client


@pytest.mark.asyncio
async def test_get_user_contract(async_client):
    response = await async_client.get("/api/get-user-contract")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_check_user(async_client):
    response = await async_client.get("/api/check-user")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_user_contract(async_client):
    response = await async_client.post("/api/update-user-contract")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_user_contract_address(async_client):
    response = await async_client.get("/api/get-user-contract-address")
    assert response.status_code == 422
