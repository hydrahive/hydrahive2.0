"""Tests für teamchat/messages.py — send_message + history (TDD).

Lazy imports in jeder Testfunktion (settings.data_dir-Freeze-Gotcha).
ensure_identity und build_client vollständig gemockt.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tokens(user_id: str, access_token: str = "tok_x", device_id: str = "DEV"):
    from hydrahive.teamchat.client import AccountTokens
    return AccountTokens(user_id=user_id, access_token=access_token, device_id=device_id)


def _make_room_send_response(event_id: str):
    import nio
    resp = MagicMock(spec=nio.RoomSendResponse)
    resp.event_id = event_id
    return resp


def _make_room_send_error():
    import nio
    return MagicMock(spec=nio.RoomSendError)


def _make_text_event(event_id: str, sender: str, body: str, ts: int):
    """Construct a real nio.RoomMessageText instance for isinstance checks."""
    import nio
    source = {
        "event_id": event_id,
        "sender": sender,
        "origin_server_ts": ts,
        "type": "m.room.message",
        "content": {"msgtype": "m.text", "body": body},
    }
    return nio.RoomMessageText(source=source, body=body, formatted_body=None, format=None)


def _make_non_text_event(event_id: str, sender: str):
    """A non-text event that must be filtered out (use RoomMessageImage as stand-in)."""
    import nio
    source = {
        "event_id": event_id,
        "sender": sender,
        "origin_server_ts": 9000,
        "type": "m.room.message",
        "content": {
            "msgtype": "m.image",
            "body": "image.png",
            "url": "mxc://test/abc",
        },
    }
    return nio.RoomMessageImage(source=source, body="image.png", url="mxc://test/abc")


def _make_room_messages_response(chunk: list):
    import nio
    resp = MagicMock(spec=nio.RoomMessagesResponse)
    resp.chunk = chunk
    return resp


def _make_room_messages_error():
    import nio
    return MagicMock(spec=nio.RoomMessagesError)


def _make_nio_client(send_resp=None, messages_resp=None):
    client = MagicMock()
    client.room_send = AsyncMock(return_value=send_resp)
    client.room_messages = AsyncMock(return_value=messages_resp)
    client.close = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# send_message — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_message_returns_dict(setup_test_env):
    """send_message gibt dict mit event_id, sender (MXID), text zurück."""
    tokens = _make_tokens("@alice:test.local", "tok_alice")
    event_id = "$ev1:test.local"
    mock_client = _make_nio_client(send_resp=_make_room_send_response(event_id))

    with (
        patch(
            "hydrahive.teamchat.messages.ensure_identity",
            new=AsyncMock(return_value=tokens),
        ),
        patch(
            "hydrahive.teamchat.messages.build_client",
            return_value=mock_client,
        ),
    ):
        from hydrahive.teamchat.messages import send_message
        result = await send_message("!room:test.local", "alice", "Hello world")

    assert result["event_id"] == event_id
    assert result["sender"] == "@alice:test.local"
    assert result["text"] == "Hello world"


@pytest.mark.asyncio
async def test_send_message_calls_room_send_with_correct_content(setup_test_env):
    """room_send wird mit msgtype m.room.message und body-Content aufgerufen."""
    tokens = _make_tokens("@alice:test.local")
    mock_client = _make_nio_client(
        send_resp=_make_room_send_response("$ev2:test.local")
    )

    with (
        patch(
            "hydrahive.teamchat.messages.ensure_identity",
            new=AsyncMock(return_value=tokens),
        ),
        patch(
            "hydrahive.teamchat.messages.build_client",
            return_value=mock_client,
        ),
    ):
        from hydrahive.teamchat.messages import send_message
        await send_message("!room:test.local", "alice", "Test body")

    mock_client.room_send.assert_awaited_once_with(
        "!room:test.local",
        message_type="m.room.message",
        content={"msgtype": "m.text", "body": "Test body"},
    )


@pytest.mark.asyncio
async def test_send_message_closes_client(setup_test_env):
    """close() wird immer aufgerufen — auch im Erfolgsfall."""
    tokens = _make_tokens("@alice:test.local")
    mock_client = _make_nio_client(
        send_resp=_make_room_send_response("$ev3:test.local")
    )

    with (
        patch(
            "hydrahive.teamchat.messages.ensure_identity",
            new=AsyncMock(return_value=tokens),
        ),
        patch(
            "hydrahive.teamchat.messages.build_client",
            return_value=mock_client,
        ),
    ):
        from hydrahive.teamchat.messages import send_message
        await send_message("!room:test.local", "alice", "Hi")

    mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# send_message — error path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_message_raises_message_error_on_send_error(setup_test_env):
    """RoomSendError-Response → MessageError; close() trotzdem aufgerufen."""
    tokens = _make_tokens("@alice:test.local")
    mock_client = _make_nio_client(send_resp=_make_room_send_error())

    with (
        patch(
            "hydrahive.teamchat.messages.ensure_identity",
            new=AsyncMock(return_value=tokens),
        ),
        patch(
            "hydrahive.teamchat.messages.build_client",
            return_value=mock_client,
        ),
    ):
        from hydrahive.teamchat.messages import send_message, MessageError
        with pytest.raises(MessageError):
            await send_message("!room:test.local", "alice", "Boom")

    mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# history — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_history_returns_chronological_text_messages(setup_test_env):
    """history gibt nur m.text-Events zurück, chronologisch (älteste zuerst).

    direction=back → Matrix liefert neueste zuerst → muss reversed werden.
    """
    tokens = _make_tokens("@bob:test.local")

    # Matrix back-direction: newest first (ev2 newer, ev1 older)
    ev_newer = _make_text_event("$ev2:test.local", "@alice:test.local", "Second", ts=2000)
    ev_older = _make_text_event("$ev1:test.local", "@bob:test.local", "First", ts=1000)
    non_text = _make_non_text_event("$img1:test.local", "@carol:test.local")

    # chunk: newest-first order from back-direction (ev_newer, non_text, ev_older)
    chunk = [ev_newer, non_text, ev_older]
    mock_client = _make_nio_client(
        messages_resp=_make_room_messages_response(chunk)
    )

    with (
        patch(
            "hydrahive.teamchat.messages.ensure_identity",
            new=AsyncMock(return_value=tokens),
        ),
        patch(
            "hydrahive.teamchat.messages.build_client",
            return_value=mock_client,
        ),
    ):
        from hydrahive.teamchat.messages import history
        result = await history("!room:test.local", "bob", limit=50)

    # non-text event filtered out
    assert len(result) == 2

    # chronological order: ev_older first, ev_newer second
    assert result[0]["event_id"] == "$ev1:test.local"
    assert result[0]["sender"] == "@bob:test.local"
    assert result[0]["text"] == "First"
    assert result[0]["ts"] == 1000

    assert result[1]["event_id"] == "$ev2:test.local"
    assert result[1]["sender"] == "@alice:test.local"
    assert result[1]["text"] == "Second"
    assert result[1]["ts"] == 2000


@pytest.mark.asyncio
async def test_history_calls_room_messages_with_direction_back(setup_test_env):
    """room_messages wird mit direction=back und korrektem limit aufgerufen."""
    import nio
    tokens = _make_tokens("@bob:test.local")
    mock_client = _make_nio_client(
        messages_resp=_make_room_messages_response([])
    )

    with (
        patch(
            "hydrahive.teamchat.messages.ensure_identity",
            new=AsyncMock(return_value=tokens),
        ),
        patch(
            "hydrahive.teamchat.messages.build_client",
            return_value=mock_client,
        ),
    ):
        from hydrahive.teamchat.messages import history
        await history("!room:test.local", "bob", limit=25)

    mock_client.room_messages.assert_awaited_once_with(
        "!room:test.local",
        start="",
        limit=25,
        direction=nio.MessageDirection.back,
    )


@pytest.mark.asyncio
async def test_history_closes_client(setup_test_env):
    """close() wird immer aufgerufen — auch im Erfolgsfall."""
    tokens = _make_tokens("@bob:test.local")
    mock_client = _make_nio_client(
        messages_resp=_make_room_messages_response([])
    )

    with (
        patch(
            "hydrahive.teamchat.messages.ensure_identity",
            new=AsyncMock(return_value=tokens),
        ),
        patch(
            "hydrahive.teamchat.messages.build_client",
            return_value=mock_client,
        ),
    ):
        from hydrahive.teamchat.messages import history
        await history("!room:test.local", "bob")

    mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# history — error path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_history_raises_message_error_on_messages_error(setup_test_env):
    """RoomMessagesError-Response → MessageError; close() trotzdem aufgerufen."""
    tokens = _make_tokens("@bob:test.local")
    mock_client = _make_nio_client(messages_resp=_make_room_messages_error())

    with (
        patch(
            "hydrahive.teamchat.messages.ensure_identity",
            new=AsyncMock(return_value=tokens),
        ),
        patch(
            "hydrahive.teamchat.messages.build_client",
            return_value=mock_client,
        ),
    ):
        from hydrahive.teamchat.messages import history, MessageError
        with pytest.raises(MessageError):
            await history("!room:test.local", "bob")

    mock_client.close.assert_awaited_once()
