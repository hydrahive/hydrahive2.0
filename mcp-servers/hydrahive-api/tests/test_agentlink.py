import asyncio
import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from _agentlink import AgentLinkClient

def make_al(base_url: str, token: str) -> AgentLinkClient:
    auth = Auth(base_url=base_url, api_key=token)
    return AgentLinkClient(rest=RestClient(auth), agent_id="claude-code", base_url=base_url)

@pytest.mark.asyncio
async def test_send_state(base_url, token):
    with respx.mock:
        respx.post(f"{base_url}/agentlink/api/states").mock(
            return_value=httpx.Response(201, json={
                "id": "state-1",
                "agent_id": "claude-code",
                "task": {"type": "feature", "description": "test", "priority": 5, "status": "in_progress"}
            })
        )
        al = make_al(base_url, token)
        state = await al.send_state(to_agent="buddy", task_type="feature", description="Bitte erledige X")
        assert state["id"] == "state-1"

@pytest.mark.asyncio
async def test_reply_to_handoff(base_url, token):
    with respx.mock:
        respx.post(f"{base_url}/agentlink/api/states").mock(
            return_value=httpx.Response(201, json={"id": "reply-1", "agent_id": "claude-code"})
        )
        al = make_al(base_url, token)
        result = await al.reply_to_handoff("state-99", "Erledigt!")
        assert result["id"] == "reply-1"

def test_drain_inbox_leer(base_url, token):
    al = make_al(base_url, token)
    assert al.drain_inbox() == []

@pytest.mark.asyncio
async def test_eingehender_handoff_in_queue(base_url, token):
    al = make_al(base_url, token)
    await al._queue.put({"id": "state-99", "task": {"description": "Tue das"}})
    result = al.drain_inbox()
    assert len(result) == 1
    assert result[0]["id"] == "state-99"

def test_al_urls(base_url, token):
    al = make_al(base_url, token)
    assert al.al_ws_url == "wss://192.168.3.22/agentlink/ws/"
    assert al.al_rest_base == "https://192.168.3.22/agentlink/api"

def test_is_connected_initial_false(base_url, token):
    al = make_al(base_url, token)
    assert al.is_connected() is False

def test_last_error_initial_none(base_url, token):
    al = make_al(base_url, token)
    assert al.last_error() is None

@pytest.mark.asyncio
async def test_handle_message_handoff_received(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/agentlink/api/states/state-42").mock(
            return_value=httpx.Response(200, json={"id": "state-42", "task": {"description": "do it"}})
        )
        al = make_al(base_url, token)
        await al._handle_message('{"type": "handoff_received", "state_id": "state-42"}')
        result = al.drain_inbox()
        assert len(result) == 1
        assert result[0]["id"] == "state-42"

@pytest.mark.asyncio
async def test_handle_message_unbekannter_typ_ignoriert(base_url, token):
    al = make_al(base_url, token)
    await al._handle_message('{"type": "ping"}')
    assert al.drain_inbox() == []
