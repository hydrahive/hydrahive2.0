import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from tools.agents import list_agents, get_agent, update_agent


@pytest.mark.asyncio
async def test_list_agents(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/agents").mock(
            return_value=httpx.Response(200, json=[{"id": "buddy", "name": "Buddy"}])
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await list_agents(RestClient(auth))
        assert result[0]["id"] == "buddy"


@pytest.mark.asyncio
async def test_get_agent(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/agents/buddy").mock(
            return_value=httpx.Response(200, json={"id": "buddy", "max_tokens": 16384})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await get_agent(RestClient(auth), "buddy")
        assert result["max_tokens"] == 16384


@pytest.mark.asyncio
async def test_update_agent(base_url, token):
    with respx.mock:
        respx.patch(f"{base_url}/api/agents/buddy").mock(
            return_value=httpx.Response(200, json={"id": "buddy", "max_tokens": 8192})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await update_agent(RestClient(auth), "buddy", "max_tokens", 8192)
        assert result["max_tokens"] == 8192
