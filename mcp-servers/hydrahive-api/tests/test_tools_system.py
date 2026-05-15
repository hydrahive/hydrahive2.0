import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from tools.system import get_status, get_token_stats


@pytest.mark.asyncio
async def test_get_status(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/health").mock(
            return_value=httpx.Response(200, json={"status": "healthy", "version": "2.1.0"})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await get_status(RestClient(auth))
        assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_status_fehler_gibt_error_dict(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/health").mock(return_value=httpx.Response(500))
        auth = Auth(base_url=base_url, api_key=token)
        result = await get_status(RestClient(auth))
        assert "error" in result
        assert result["code"] == "health_failed"


@pytest.mark.asyncio
async def test_get_token_stats(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/dashboard").mock(
            return_value=httpx.Response(200, json={"total_cost_usd": 12.50})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await get_token_stats(RestClient(auth))
        assert result["total_cost_usd"] == 12.50
