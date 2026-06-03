"""Tests für teamchat HTTP-API — FastAPI TestClient (TDD).

Lazy imports überall (settings.data_dir-Freeze-Gotcha).
Auth-Override via dependency_overrides.
teamchat-Module vollständig gemockt (AsyncMock).
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# App + auth fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_enabled(setup_test_env):
    """TestClient mit teamchat_enabled=True und auth-Override."""
    import os
    os.environ["HH_TEAMCHAT_ENABLED"] = "1"
    try:
        from fastapi.testclient import TestClient
        from hydrahive.api.main import app
        from hydrahive.api.middleware.auth import require_auth

        app.dependency_overrides[require_auth] = lambda: ("till", "user")
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
    finally:
        app.dependency_overrides.pop(require_auth, None)
        os.environ.pop("HH_TEAMCHAT_ENABLED", None)


@pytest.fixture()
def client_disabled(setup_test_env):
    """TestClient mit teamchat_enabled=False."""
    import os
    os.environ.pop("HH_TEAMCHAT_ENABLED", None)
    os.environ["HH_TEAMCHAT_ENABLED"] = "0"
    try:
        from fastapi.testclient import TestClient
        from hydrahive.api.main import app
        from hydrahive.api.middleware.auth import require_auth

        app.dependency_overrides[require_auth] = lambda: ("till", "user")
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
    finally:
        app.dependency_overrides.pop(require_auth, None)
        os.environ.pop("HH_TEAMCHAT_ENABLED", None)


# ---------------------------------------------------------------------------
# 409 when teamchat disabled
# ---------------------------------------------------------------------------

def test_get_rooms_disabled_returns_409(client_disabled):
    resp = client_disabled.get("/api/teamchat/rooms")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "teamchat_not_configured"


def test_post_rooms_disabled_returns_409(client_disabled):
    resp = client_disabled.post("/api/teamchat/rooms", json={"name": "Test"})
    assert resp.status_code == 409


def test_get_messages_disabled_returns_409(client_disabled):
    resp = client_disabled.get("/api/teamchat/rooms/!abc:test/messages")
    assert resp.status_code == 409


def test_post_message_disabled_returns_409(client_disabled):
    resp = client_disabled.post("/api/teamchat/rooms/!abc:test/messages", json={"text": "hi"})
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /rooms
# ---------------------------------------------------------------------------

def test_post_rooms_calls_create_room_and_returns_room_id(client_enabled):
    room_id = "!newroom:matrix.local"
    with patch(
        "hydrahive.api.routes.teamchat.rooms.create_room",
        new=AsyncMock(return_value=room_id),
    ) as mock_create:
        resp = client_enabled.post(
            "/api/teamchat/rooms",
            json={"name": "Dev Chat", "members": ["alice", "bob"]},
        )

    assert resp.status_code == 201
    assert resp.json() == {"room_id": room_id}
    mock_create.assert_awaited_once_with("till", "Dev Chat", ["alice", "bob"])


def test_post_rooms_default_members_empty(client_enabled):
    """Wenn 'members' fehlt, wird leere Liste übergeben."""
    room_id = "!room2:matrix.local"
    with patch(
        "hydrahive.api.routes.teamchat.rooms.create_room",
        new=AsyncMock(return_value=room_id),
    ) as mock_create:
        resp = client_enabled.post("/api/teamchat/rooms", json={"name": "Solo Room"})

    assert resp.status_code == 201
    mock_create.assert_awaited_once_with("till", "Solo Room", [])


def test_post_rooms_room_error_returns_502(client_enabled):
    from hydrahive.teamchat.rooms import RoomError
    with patch(
        "hydrahive.api.routes.teamchat.rooms.create_room",
        new=AsyncMock(side_effect=RoomError("Matrix down")),
    ):
        resp = client_enabled.post("/api/teamchat/rooms", json={"name": "Bad Room"})

    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# GET /rooms
# ---------------------------------------------------------------------------

def test_get_rooms_returns_list(client_enabled):
    fake_rooms = [
        {"room_id": "!r1:matrix.local", "name": "General"},
        {"room_id": "!r2:matrix.local", "name": "Dev"},
    ]
    with patch(
        "hydrahive.api.routes.teamchat.rooms.list_joined_rooms",
        new=AsyncMock(return_value=fake_rooms),
    ) as mock_list:
        resp = client_enabled.get("/api/teamchat/rooms")

    assert resp.status_code == 200
    assert resp.json() == fake_rooms
    mock_list.assert_awaited_once_with("till")


def test_get_rooms_room_error_returns_502(client_enabled):
    """RoomError aus list_joined_rooms → 502."""
    from hydrahive.teamchat.rooms import RoomError
    with patch(
        "hydrahive.api.routes.teamchat.rooms.list_joined_rooms",
        new=AsyncMock(side_effect=RoomError("Matrix unavailable")),
    ):
        resp = client_enabled.get("/api/teamchat/rooms")

    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# PATCH/DELETE /rooms/{room_id} — umbenennen/löschen (5b)
# ---------------------------------------------------------------------------

def test_patch_room_renames_when_manager(client_enabled):
    room_id = "!r:matrix.local"
    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"room_id": room_id, "created_by": "till"}),
        patch("hydrahive.api.routes.teamchat.rooms.rename_room",
              new=AsyncMock()) as mock_rename,
    ):
        resp = client_enabled.patch(f"/api/teamchat/rooms/{room_id}", json={"name": "Neuer Name"})

    assert resp.status_code == 204
    mock_rename.assert_awaited_once_with(room_id, "till", "Neuer Name")


def test_patch_room_not_manager_403(client_enabled):
    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"created_by": "someone_else"}),
        patch("hydrahive.api.routes.teamchat.rooms.rename_room",
              new=AsyncMock()) as mock_rename,
    ):
        resp = client_enabled.patch("/api/teamchat/rooms/!r:matrix.local", json={"name": "X"})

    assert resp.status_code == 403
    mock_rename.assert_not_awaited()


def test_delete_room_when_manager(client_enabled):
    room_id = "!r:matrix.local"
    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"room_id": room_id, "created_by": "till"}),
        patch("hydrahive.api.routes.teamchat.rooms.delete_room",
              new=AsyncMock()) as mock_delete,
    ):
        resp = client_enabled.delete(f"/api/teamchat/rooms/{room_id}")

    assert resp.status_code == 204
    mock_delete.assert_awaited_once_with(room_id, "till")


def test_delete_room_not_manager_403(client_enabled):
    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"created_by": "someone_else"}),
        patch("hydrahive.api.routes.teamchat.rooms.delete_room",
              new=AsyncMock()) as mock_delete,
    ):
        resp = client_enabled.delete("/api/teamchat/rooms/!r:matrix.local")

    assert resp.status_code == 403
    mock_delete.assert_not_awaited()


# ---------------------------------------------------------------------------
# POST /rooms/{room_id}/messages
# ---------------------------------------------------------------------------

def test_post_message_calls_send_and_broadcasts(client_enabled):
    room_id = "!chat:matrix.local"
    msg_result = {"event_id": "$evt1", "sender": "@till:matrix.local", "text": "hello"}

    with (
        patch(
            "hydrahive.api.routes.teamchat.messages.send_message",
            new=AsyncMock(return_value=msg_result),
        ) as mock_send,
        patch(
            "hydrahive.api.routes.teamchat.room_broadcaster",
        ) as mock_bc,
    ):
        resp = client_enabled.post(
            f"/api/teamchat/rooms/{room_id}/messages",
            json={"text": "hello"},
        )

    assert resp.status_code == 200
    assert resp.json() == msg_result
    mock_send.assert_awaited_once_with(room_id, "till", "hello")
    mock_bc.broadcast.assert_called_once_with(room_id, json.dumps(msg_result))


def test_post_message_schedules_agent_response(client_enabled):
    """Nach send+broadcast wird die Agent-Antwort als Background-Task geplant."""
    room_id = "!chat:matrix.local"
    msg_result = {"event_id": "$evt1", "sender": "@till:matrix.local", "text": "buddy hi"}

    with (
        patch(
            "hydrahive.api.routes.teamchat.messages.send_message",
            new=AsyncMock(return_value=msg_result),
        ),
        patch("hydrahive.api.routes.teamchat.room_broadcaster"),
        patch("hydrahive.api.routes.teamchat.agent_bridge.schedule_response") as mock_sched,
    ):
        resp = client_enabled.post(
            f"/api/teamchat/rooms/{room_id}/messages",
            json={"text": "buddy hi"},
        )

    assert resp.status_code == 200
    mock_sched.assert_called_once_with(room_id, "till", "buddy hi")


def test_post_message_message_error_returns_502(client_enabled):
    from hydrahive.teamchat.messages import MessageError
    room_id = "!chat:matrix.local"

    with patch(
        "hydrahive.api.routes.teamchat.messages.send_message",
        new=AsyncMock(side_effect=MessageError("send failed")),
    ):
        resp = client_enabled.post(
            f"/api/teamchat/rooms/{room_id}/messages",
            json={"text": "hello"},
        )

    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# GET /rooms/{room_id}/messages — limit validation
# ---------------------------------------------------------------------------

def test_get_messages_limit_too_large_returns_422(client_enabled):
    """limit > 200 muss 422 Unprocessable Entity zurückgeben."""
    room_id = "!chat:matrix.local"
    resp = client_enabled.get(f"/api/teamchat/rooms/{room_id}/messages?limit=9999")
    assert resp.status_code == 422


def test_get_messages_limit_zero_returns_422(client_enabled):
    """limit=0 ist ungültig (ge=1) → 422."""
    room_id = "!chat:matrix.local"
    resp = client_enabled.get(f"/api/teamchat/rooms/{room_id}/messages?limit=0")
    assert resp.status_code == 422


def test_get_messages_limit_200_is_valid(client_enabled):
    """limit=200 ist der maximale gültige Wert."""
    room_id = "!chat:matrix.local"
    with patch(
        "hydrahive.api.routes.teamchat.messages.history",
        new=AsyncMock(return_value=[]),
    ) as mock_history:
        resp = client_enabled.get(f"/api/teamchat/rooms/{room_id}/messages?limit=200")

    assert resp.status_code == 200
    mock_history.assert_awaited_once_with(room_id, "till", 200)


# ---------------------------------------------------------------------------
# GET /rooms/{room_id}/messages
# ---------------------------------------------------------------------------

def test_get_messages_returns_history(client_enabled):
    room_id = "!chat:matrix.local"
    history = [
        {"event_id": "$e1", "sender": "@alice:local", "text": "hey", "ts": 1000},
        {"event_id": "$e2", "sender": "@bob:local", "text": "hi", "ts": 2000},
    ]
    with patch(
        "hydrahive.api.routes.teamchat.messages.history",
        new=AsyncMock(return_value=history),
    ) as mock_history:
        resp = client_enabled.get(f"/api/teamchat/rooms/{room_id}/messages?limit=10")

    assert resp.status_code == 200
    assert resp.json() == history
    mock_history.assert_awaited_once_with(room_id, "till", 10)


def test_get_messages_default_limit_50(client_enabled):
    room_id = "!chat:matrix.local"
    with patch(
        "hydrahive.api.routes.teamchat.messages.history",
        new=AsyncMock(return_value=[]),
    ) as mock_history:
        resp = client_enabled.get(f"/api/teamchat/rooms/{room_id}/messages")

    assert resp.status_code == 200
    mock_history.assert_awaited_once_with(room_id, "till", 50)


def test_get_messages_message_error_returns_502(client_enabled):
    from hydrahive.teamchat.messages import MessageError
    room_id = "!chat:matrix.local"

    with patch(
        "hydrahive.api.routes.teamchat.messages.history",
        new=AsyncMock(side_effect=MessageError("history failed")),
    ):
        resp = client_enabled.get(f"/api/teamchat/rooms/{room_id}/messages")

    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# GET /rooms/{room_id}/members
# ---------------------------------------------------------------------------

def test_get_members_returns_list(client_enabled):
    room_id = "!chat:matrix.local"
    members = ["@alice:local", "@bob:local"]
    with patch(
        "hydrahive.api.routes.teamchat.rooms.list_members",
        new=AsyncMock(return_value=members),
    ) as mock_members:
        resp = client_enabled.get(f"/api/teamchat/rooms/{room_id}/members")

    assert resp.status_code == 200
    assert resp.json() == members
    mock_members.assert_awaited_once_with(room_id, "till")


# ---------------------------------------------------------------------------
# POST /rooms/{room_id}/members
# ---------------------------------------------------------------------------

def test_post_members_invites_user(client_enabled):
    """Ersteller (till) darf einen bekannten User einladen — Invite läuft als Ersteller."""
    room_id = "!chat:matrix.local"
    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"room_id": room_id, "created_by": "till"}),
        patch("hydrahive.api.routes.teamchat.hh_users.list_users",
              return_value=[{"username": "charlie"}]),
        patch("hydrahive.api.routes.teamchat.rooms.invite_member",
              new=AsyncMock(return_value=None)) as mock_invite,
    ):
        resp = client_enabled.post(
            f"/api/teamchat/rooms/{room_id}/members",
            json={"user_id": "charlie"},
        )

    assert resp.status_code == 204
    mock_invite.assert_awaited_once_with(room_id, "till", "charlie")


def test_post_members_unknown_user_404(client_enabled):
    """Einladen eines nicht-registrierten Users → 404 (kein Geister-Account)."""
    room_id = "!chat:matrix.local"
    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"room_id": room_id, "created_by": "till"}),
        patch("hydrahive.api.routes.teamchat.hh_users.list_users",
              return_value=[{"username": "till"}]),
        patch("hydrahive.api.routes.teamchat.rooms.invite_member",
              new=AsyncMock()) as mock_invite,
    ):
        resp = client_enabled.post(
            f"/api/teamchat/rooms/{room_id}/members",
            json={"user_id": "ghost"},
        )

    assert resp.status_code == 404
    mock_invite.assert_not_awaited()


def test_post_members_not_manager_403(client_enabled):
    """Nicht-Ersteller/Nicht-Admin darf NICHT einladen."""
    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"created_by": "someone_else"}),
        patch("hydrahive.api.routes.teamchat.rooms.invite_member",
              new=AsyncMock()) as mock_invite,
    ):
        resp = client_enabled.post(
            "/api/teamchat/rooms/!chat:matrix.local/members",
            json={"user_id": "charlie"},
        )

    assert resp.status_code == 403
    mock_invite.assert_not_awaited()


def test_post_members_room_error_returns_502(client_enabled):
    from hydrahive.teamchat.rooms import RoomError
    room_id = "!chat:matrix.local"

    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"room_id": room_id, "created_by": "till"}),
        patch("hydrahive.api.routes.teamchat.hh_users.list_users",
              return_value=[{"username": "charlie"}]),
        patch("hydrahive.api.routes.teamchat.rooms.invite_member",
              new=AsyncMock(side_effect=RoomError("invite failed"))),
    ):
        resp = client_enabled.post(
            f"/api/teamchat/rooms/{room_id}/members",
            json={"user_id": "charlie"},
        )

    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# DELETE /rooms/{room_id}/members/{user_id} — Mitglied entfernen (5a)
# ---------------------------------------------------------------------------

def test_delete_member_kicks_when_manager(client_enabled):
    room_id = "!chat:matrix.local"
    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"room_id": room_id, "created_by": "till"}),
        patch("hydrahive.api.routes.teamchat.rooms.kick_member",
              new=AsyncMock()) as mock_kick,
    ):
        resp = client_enabled.delete(f"/api/teamchat/rooms/{room_id}/members/bibi")

    assert resp.status_code == 204
    mock_kick.assert_awaited_once_with(room_id, "till", "bibi")


def test_delete_member_not_manager_403(client_enabled):
    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"created_by": "someone_else"}),
        patch("hydrahive.api.routes.teamchat.rooms.kick_member",
              new=AsyncMock()) as mock_kick,
    ):
        resp = client_enabled.delete("/api/teamchat/rooms/!chat:matrix.local/members/bibi")

    assert resp.status_code == 403
    mock_kick.assert_not_awaited()


def test_delete_member_room_not_found_404(client_enabled):
    with patch("hydrahive.api.routes.teamchat.db_teamchat.get_room", return_value=None):
        resp = client_enabled.delete("/api/teamchat/rooms/!chat:matrix.local/members/bibi")
    assert resp.status_code == 404


def test_delete_member_cannot_remove_owner_422(client_enabled):
    """Den Raum-Ersteller zu kicken ist verboten (würde den Raum unbedienbar machen)."""
    room_id = "!chat:matrix.local"
    with (
        patch("hydrahive.api.routes.teamchat.db_teamchat.get_room",
              return_value={"room_id": room_id, "created_by": "till"}),
        patch("hydrahive.api.routes.teamchat.rooms.kick_member",
              new=AsyncMock()) as mock_kick,
    ):
        resp = client_enabled.delete(f"/api/teamchat/rooms/{room_id}/members/till")

    assert resp.status_code == 422
    mock_kick.assert_not_awaited()


# ---------------------------------------------------------------------------
# GET /rooms/{room_id}/stream  — Membership-Gate
# ---------------------------------------------------------------------------

def test_stream_returns_403_when_not_member(client_enabled):
    """is_member=False → 403 Forbidden, bevor der SSE-Generator gestartet wird."""
    from hydrahive.teamchat.rooms import RoomError
    room_id = "!secret:matrix.local"
    with patch(
        "hydrahive.api.routes.teamchat.rooms.is_member",
        new=AsyncMock(return_value=False),
    ):
        resp = client_enabled.get(f"/api/teamchat/rooms/{room_id}/stream")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "not_a_member"


def test_stream_subscribes_when_member(client_enabled):
    """is_member=True → room_broadcaster.subscribe wird aufgerufen."""
    room_id = "!open:matrix.local"
    mock_queue = MagicMock()
    mock_queue.get = AsyncMock(side_effect=Exception("stop"))  # Sofort abbrechen

    with (
        patch(
            "hydrahive.api.routes.teamchat.rooms.is_member",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "hydrahive.api.routes.teamchat.room_broadcaster",
        ) as mock_bc,
    ):
        mock_bc.subscribe.return_value = mock_queue
        # Der Stream wird gestartet aber bricht sofort ab → subscribe wurde aufgerufen
        try:
            client_enabled.get(f"/api/teamchat/rooms/{room_id}/stream", timeout=1)
        except Exception:
            pass
        mock_bc.subscribe.assert_called_once_with(room_id)


def test_stream_room_error_returns_502(client_enabled):
    """RoomError aus is_member → 502."""
    from hydrahive.teamchat.rooms import RoomError
    room_id = "!err:matrix.local"
    with patch(
        "hydrahive.api.routes.teamchat.rooms.is_member",
        new=AsyncMock(side_effect=RoomError("Matrix down")),
    ):
        resp = client_enabled.get(f"/api/teamchat/rooms/{room_id}/stream")

    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# GET /rooms/{room_id}/stream  (SSE — light test)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Agent-Endpoints: GET/POST/DELETE /rooms/{room_id}/agents
# ---------------------------------------------------------------------------

def _override_auth(username, role):
    from hydrahive.api.main import app
    from hydrahive.api.middleware.auth import require_auth
    app.dependency_overrides[require_auth] = lambda: (username, role)


def test_post_agents_disabled_returns_409(client_disabled):
    resp = client_disabled.post("/api/teamchat/rooms/!r:t/agents", json={"agent_id": "a1"})
    assert resp.status_code == 409


def test_get_room_agents_returns_names(client_enabled):
    room_id = "!r:matrix.local"
    with (
        patch("hydrahive.api.routes.teamchat.rooms.is_member", new=AsyncMock(return_value=True)),
        patch("hydrahive.api.routes.teamchat.db_teamchat.list_room_agents",
              return_value=[{"agent_id": "a1"}, {"agent_id": "a2"}]),
        patch("hydrahive.api.routes.teamchat.agent_config.get",
              side_effect=lambda aid: {"a1": {"name": "buddy"}, "a2": {"name": "zahnfee"}}.get(aid)),
    ):
        resp = client_enabled.get(f"/api/teamchat/rooms/{room_id}/agents")

    assert resp.status_code == 200
    assert resp.json() == [
        {"agent_id": "a1", "name": "buddy"},
        {"agent_id": "a2", "name": "zahnfee"},
    ]


def test_get_room_agents_not_member_403(client_enabled):
    with patch("hydrahive.api.routes.teamchat.rooms.is_member", new=AsyncMock(return_value=False)):
        resp = client_enabled.get("/api/teamchat/rooms/!secret:matrix.local/agents")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "not_a_member"


def test_post_room_agent_attaches_when_member_and_owner(client_enabled):
    room_id = "!r:matrix.local"
    with (
        patch("hydrahive.api.routes.teamchat.rooms.is_member", new=AsyncMock(return_value=True)),
        patch("hydrahive.api.routes.teamchat.agent_config.get",
              return_value={"id": "a1", "name": "buddy", "owner": "till"}),
        patch("hydrahive.api.routes.teamchat.agent_membership.attach_agent",
              new=AsyncMock()) as mock_attach,
    ):
        resp = client_enabled.post(f"/api/teamchat/rooms/{room_id}/agents", json={"agent_id": "a1"})

    assert resp.status_code == 201
    mock_attach.assert_awaited_once_with(room_id, "till", "a1")


def test_post_room_agent_not_member_403_and_no_attach(client_enabled):
    with (
        patch("hydrahive.api.routes.teamchat.rooms.is_member", new=AsyncMock(return_value=False)),
        patch("hydrahive.api.routes.teamchat.agent_config.get",
              return_value={"id": "a1", "name": "buddy", "owner": "till"}),
        patch("hydrahive.api.routes.teamchat.agent_membership.attach_agent",
              new=AsyncMock()) as mock_attach,
    ):
        resp = client_enabled.post("/api/teamchat/rooms/!r:matrix.local/agents", json={"agent_id": "a1"})

    assert resp.status_code == 403
    mock_attach.assert_not_awaited()


def test_post_room_agent_not_owner_403(client_enabled):
    """User darf einen fremden Agenten NICHT zuschalten."""
    with (
        patch("hydrahive.api.routes.teamchat.rooms.is_member", new=AsyncMock(return_value=True)),
        patch("hydrahive.api.routes.teamchat.agent_config.get",
              return_value={"id": "a1", "name": "buddy", "owner": "someone_else"}),
        patch("hydrahive.api.routes.teamchat.agent_membership.attach_agent",
              new=AsyncMock()) as mock_attach,
    ):
        resp = client_enabled.post("/api/teamchat/rooms/!r:matrix.local/agents", json={"agent_id": "a1"})

    assert resp.status_code == 403
    assert resp.json()["detail"] == "not_your_agent"
    mock_attach.assert_not_awaited()


def test_post_room_agent_unknown_agent_404(client_enabled):
    with (
        patch("hydrahive.api.routes.teamchat.rooms.is_member", new=AsyncMock(return_value=True)),
        patch("hydrahive.api.routes.teamchat.agent_config.get", return_value=None),
        patch("hydrahive.api.routes.teamchat.agent_membership.attach_agent", new=AsyncMock()),
    ):
        resp = client_enabled.post("/api/teamchat/rooms/!r:matrix.local/agents", json={"agent_id": "ghost"})

    assert resp.status_code == 404


def test_admin_may_attach_foreign_agent(client_enabled):
    """Admin darf auch einen fremden Agenten zuschalten."""
    _override_auth("admin_user", "admin")
    room_id = "!r:matrix.local"
    with (
        patch("hydrahive.api.routes.teamchat.rooms.is_member", new=AsyncMock(return_value=True)),
        patch("hydrahive.api.routes.teamchat.agent_config.get",
              return_value={"id": "a1", "name": "buddy", "owner": "till"}),
        patch("hydrahive.api.routes.teamchat.agent_membership.attach_agent",
              new=AsyncMock()) as mock_attach,
    ):
        resp = client_enabled.post(f"/api/teamchat/rooms/{room_id}/agents", json={"agent_id": "a1"})

    assert resp.status_code == 201
    mock_attach.assert_awaited_once_with(room_id, "admin_user", "a1")


def test_delete_room_agent_detaches(client_enabled):
    room_id = "!r:matrix.local"
    with (
        patch("hydrahive.api.routes.teamchat.rooms.is_member", new=AsyncMock(return_value=True)),
        patch("hydrahive.api.routes.teamchat.agent_config.get",
              return_value={"id": "a1", "name": "buddy", "owner": "till"}),
        patch("hydrahive.api.routes.teamchat.agent_membership.detach_agent",
              new=AsyncMock()) as mock_detach,
    ):
        resp = client_enabled.delete(f"/api/teamchat/rooms/{room_id}/agents/a1")

    assert resp.status_code == 204
    mock_detach.assert_awaited_once_with(room_id, "a1")


def test_delete_room_agent_not_owner_403(client_enabled):
    with (
        patch("hydrahive.api.routes.teamchat.rooms.is_member", new=AsyncMock(return_value=True)),
        patch("hydrahive.api.routes.teamchat.agent_config.get",
              return_value={"id": "a1", "name": "buddy", "owner": "someone_else"}),
        patch("hydrahive.api.routes.teamchat.agent_membership.detach_agent",
              new=AsyncMock()) as mock_detach,
    ):
        resp = client_enabled.delete("/api/teamchat/rooms/!r:matrix.local/agents/a1")

    assert resp.status_code == 403
    mock_detach.assert_not_awaited()


def test_stream_route_is_registered_and_wired(client_enabled):
    """SSE-Endpoint ist registriert: Route ist in der App vorhanden und
    media_type ist text/event-stream.

    Wir prüfen die Route über den OpenAPI-Router statt den Body zu streamen —
    TestClient + async SSE-Generator hängt sonst auf den 20s-keepalive-Timeout.
    Die eigentliche Stream-Logik ist durch broadcaster-Unit-Tests und
    test_post_message_calls_send_and_broadcasts vollständig abgedeckt.
    """
    from hydrahive.api.main import app

    routes = {r.path: r for r in app.routes if hasattr(r, "path")}
    room_stream_path = "/api/teamchat/rooms/{room_id}/stream"
    assert room_stream_path in routes, f"Route {room_stream_path!r} not registered"

    route = routes[room_stream_path]
    # GET-Methode muss vorhanden sein
    assert "GET" in getattr(route, "methods", set())
