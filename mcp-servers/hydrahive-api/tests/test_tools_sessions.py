import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from tools.sessions import list_sessions, get_session, get_messages, send_message


@pytest.mark.asyncio
async def test_list_sessions(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/sessions").mock(
            return_value=httpx.Response(200, json=[{"id": "s1", "agent_id": "buddy"}])
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await list_sessions(RestClient(auth))
        assert result[0]["id"] == "s1"


@pytest.mark.asyncio
async def test_get_session(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/sessions/s1").mock(
            return_value=httpx.Response(200, json={"id": "s1", "total_tokens": 5000})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await get_session(RestClient(auth), "s1")
        assert result["total_tokens"] == 5000


@pytest.mark.asyncio
async def test_get_messages(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/sessions/s1/messages").mock(
            return_value=httpx.Response(200, json=[{"role": "user", "content": "Hallo"}])
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await get_messages(RestClient(auth), "s1")
        assert result[0]["content"] == "Hallo"


@pytest.mark.asyncio
async def test_send_message(base_url, token):
    with respx.mock:
        respx.post(f"{base_url}/api/sessions/s1/messages").mock(
            return_value=httpx.Response(201, json={"id": "m99", "status": "queued"})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await send_message(RestClient(auth), "s1", "Test")
        assert result["status"] == "queued"
