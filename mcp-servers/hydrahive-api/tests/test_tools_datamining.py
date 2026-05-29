import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from tools.datamining import dm_search, dm_get_session, dm_list_sessions, dm_stats


@pytest.mark.asyncio
async def test_dm_search(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/datamining/search").mock(
            return_value=httpx.Response(200, json={"results": [{"event": "test"}], "total": 1})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await dm_search(RestClient(auth), q="test")
        assert result["total"] == 1


@pytest.mark.asyncio
async def test_dm_get_session(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/datamining/sessions/s1").mock(
            return_value=httpx.Response(200, json={"session_id": "s1", "events": []})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await dm_get_session(RestClient(auth), "s1")
        assert result["session_id"] == "s1"


@pytest.mark.asyncio
async def test_dm_list_sessions(base_url, token):
    with respx.mock:
        # Echte Endpoint-Form: dict mit "sessions" (NICHT eine Liste, NICHT "items")
        respx.get(f"{base_url}/api/datamining/sessions").mock(
            return_value=httpx.Response(200, json={
                "active": True,
                "sessions": [{"session_id": "s1", "event_count": 42}],
            })
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await dm_list_sessions(RestClient(auth))
        assert result[0]["event_count"] == 42


@pytest.mark.asyncio
async def test_dm_stats(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/datamining/stats/latest").mock(
            return_value=httpx.Response(200, json={"total_cost_usd": 9.99})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await dm_stats(RestClient(auth))
        assert result["total_cost_usd"] == 9.99
