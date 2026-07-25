"""Static checks for per-instance aiohttp session reuse."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKCHAIN_CALL = (ROOT / "contract_tools" / "blockchain_call.py").read_text()
API_REQUEST = (ROOT / "contract_tools" / "api_request.py").read_text()
DEPENDENCIES = (ROOT / "api" / "dependencies.py").read_text()


def test_stellar_client_reuses_one_session_and_exposes_close():
    assert "self._session: aiohttp.ClientSession | None = None" in BLOCKCHAIN_CALL
    assert "async def _get_session(self) -> aiohttp.ClientSession" in BLOCKCHAIN_CALL
    assert "self._session = aiohttp.ClientSession()" in BLOCKCHAIN_CALL
    assert "async def close(self) -> None" in BLOCKCHAIN_CALL
    assert "await self._session.close()" in BLOCKCHAIN_CALL
    assert BLOCKCHAIN_CALL.count("aiohttp.ClientSession(") == 1
    assert "async with aiohttp.ClientSession" not in BLOCKCHAIN_CALL


def test_api_request_reuses_one_session_and_exposes_close():
    assert "self._session: aiohttp.ClientSession | None = None" in API_REQUEST
    assert "async def _get_session(self) -> aiohttp.ClientSession" in API_REQUEST
    assert "self._session = aiohttp.ClientSession(headers=self.DEFAULT_HEADER)" in API_REQUEST
    assert "async def close(self) -> None" in API_REQUEST
    assert API_REQUEST.count("aiohttp.ClientSession(") == 1
    assert "async with aiohttp.ClientSession" not in API_REQUEST


def test_fastapi_dependency_closes_stellar_client_after_request():
    assert "async def get_stellar_client() -> AsyncIterator[StellarClient]" in DEPENDENCIES
    assert "yield client" in DEPENDENCIES
    assert "await client.close()" in DEPENDENCIES