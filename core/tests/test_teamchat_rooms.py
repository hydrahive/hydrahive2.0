"""Tests für teamchat/rooms.py — Raum-Management (TDD).

Lazy imports in jeder Testfunktion (settings.data_dir-Freeze-Gotcha).
ensure_identity und build_client vollständig gemockt.
Echte DB via setup_test_env-Fixture.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _ensure_db(setup_test_env):
    """DB initialisieren + teamchat_rooms nach jedem Test leeren."""
    from hydrahive.db import init_db
    from hydrahive.db.connection import db

    init_db()
    yield
    with db() as conn:
        conn.execute("DELETE FROM teamchat_rooms")


def _make_tokens(user_id: str, access_token: str = "tok_x", device_id: str = "DEV"):
    from hydrahive.teamchat.client import AccountTokens
    return AccountTokens(user_id=user_id, access_token=access_token, device_id=device_id)


def _make_room_create_response(room_id: str):
    """Minimal nio.RoomCreateResponse mock."""
    import nio
    resp = MagicMock(spec=nio.RoomCreateResponse)
    resp.room_id = room_id
    return resp


def _make_room_create_error():
    import nio
    return MagicMock(spec=nio.RoomCreateError)


def _make_room_invite_response():
    import nio
    return MagicMock(spec=nio.RoomInviteResponse)


def _make_room_invite_error():
    import nio
    return MagicMock(spec=nio.RoomInviteError)


def _make_joined_members_response(mxids: list[str]):
    import nio
    resp = MagicMock(spec=nio.JoinedMembersResponse)
    members = []
    for mxid in mxids:
        m = MagicMock(spec=nio.RoomMember)
        m.user_id = mxid
        members.append(m)
    resp.members = members
    return resp


def _make_joined_members_error():
    import nio
    return MagicMock(spec=nio.JoinedMembersError)


def _make_nio_client(
    room_create_resp=None,
    room_invite_resp=None,
    joined_members_resp=None,
):
    """Build a MagicMock nio.AsyncClient with AsyncMock methods."""
    mock_client = MagicMock()
    mock_client.room_create = AsyncMock(return_value=room_create_resp)
    mock_client.room_invite = AsyncMock(return_value=room_invite_resp)
    mock_client.joined_members = AsyncMock(return_value=joined_members_resp)
    mock_client.close = AsyncMock()
    return mock_client


# ---------------------------------------------------------------------------
# create_room — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_room_returns_room_id(setup_test_env):
    """create_room gibt die room_id aus der Matrix-Response zurück."""
    creator_tokens = _make_tokens("@creator:test.local", "tok_creator")
    invitee_tokens = _make_tokens("@alice:test.local", "tok_alice")

    room_id = "!abc123:test.local"
    mock_client = _make_nio_client(
        room_create_resp=_make_room_create_response(room_id)
    )

    def ensure_identity_side_effect(uid):
        mapping = {"creator": creator_tokens, "alice": invitee_tokens}
        return mapping[uid]

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch(
            "hydrahive.teamchat.rooms.build_client",
            return_value=mock_client,
        ),
    ):
        from hydrahive.teamchat.rooms import create_room
        result = await create_room("creator", "Test Room", ["alice"])

    assert result == room_id


@pytest.mark.asyncio
async def test_create_room_calls_ensure_identity_for_all(setup_test_env):
    """ensure_identity wird für creator UND jeden invitee gerufen."""
    creator_tokens = _make_tokens("@creator:test.local")
    inv1_tokens = _make_tokens("@alice:test.local")
    inv2_tokens = _make_tokens("@bob:test.local")

    room_id = "!room1:test.local"
    mock_client = _make_nio_client(
        room_create_resp=_make_room_create_response(room_id)
    )

    def ensure_identity_side_effect(uid):
        mapping = {
            "creator": creator_tokens,
            "alice": inv1_tokens,
            "bob": inv2_tokens,
        }
        return mapping[uid]

    mock_ensure = AsyncMock(side_effect=ensure_identity_side_effect)

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=mock_ensure),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import create_room
        await create_room("creator", "Team", ["alice", "bob"])

    calls = [c.args[0] for c in mock_ensure.call_args_list]
    assert "creator" in calls
    assert "alice" in calls
    assert "bob" in calls
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_create_room_passes_preset_and_invitees(setup_test_env):
    """room_create wird mit preset=private_chat und invitee-MXIDs aufgerufen."""
    import nio

    creator_tokens = _make_tokens("@creator:test.local")
    alice_tokens = _make_tokens("@alice:test.local")

    room_id = "!room2:test.local"
    mock_client = _make_nio_client(
        room_create_resp=_make_room_create_response(room_id)
    )

    def ensure_identity_side_effect(uid):
        return creator_tokens if uid == "creator" else alice_tokens

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import create_room
        await create_room("creator", "My Room", ["alice"])

    mock_client.room_create.assert_awaited_once()
    kwargs = mock_client.room_create.call_args.kwargs
    assert kwargs.get("preset") == nio.RoomPreset.private_chat
    assert "@alice:test.local" in kwargs.get("invite", [])


@pytest.mark.asyncio
async def test_create_room_persists_in_db(setup_test_env):
    """Raum wird nach erfolgreichem room_create in der DB gespeichert."""
    creator_tokens = _make_tokens("@creator:test.local")
    room_id = "!persisted:test.local"
    mock_client = _make_nio_client(
        room_create_resp=_make_room_create_response(room_id)
    )

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(return_value=creator_tokens),
        ),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import create_room
        await create_room("creator", "Persisted Room", [])

    from hydrahive.db import teamchat as db
    row = db.get_room(room_id)
    assert row is not None
    assert row["name"] == "Persisted Room"
    assert row["created_by"] == "creator"


@pytest.mark.asyncio
async def test_create_room_closes_client(setup_test_env):
    """close() wird immer aufgerufen — auch im Erfolgsfall."""
    creator_tokens = _make_tokens("@creator:test.local")
    room_id = "!closetest:test.local"
    mock_client = _make_nio_client(
        room_create_resp=_make_room_create_response(room_id)
    )

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(return_value=creator_tokens),
        ),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import create_room
        await create_room("creator", "Close Test", [])

    mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# create_room — error path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_room_raises_on_error_response(setup_test_env):
    """RoomCreateError-Response → RoomError, close() trotzdem aufgerufen."""
    creator_tokens = _make_tokens("@creator:test.local")
    mock_client = _make_nio_client(
        room_create_resp=_make_room_create_error()
    )

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(return_value=creator_tokens),
        ),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import create_room, RoomError
        with pytest.raises(RoomError):
            await create_room("creator", "Bad Room", [])

    mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# invite_member
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invite_member_success(setup_test_env):
    """invite_member: room_invite mit invitee-MXID aufgerufen, kein Fehler."""
    inviter_tokens = _make_tokens("@inviter:test.local")
    invitee_tokens = _make_tokens("@guest:test.local")

    mock_client = _make_nio_client(
        room_invite_resp=_make_room_invite_response()
    )

    def ensure_identity_side_effect(uid):
        return inviter_tokens if uid == "inviter" else invitee_tokens

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import invite_member
        await invite_member("!room:test.local", "inviter", "guest")

    mock_client.room_invite.assert_awaited_once_with("!room:test.local", "@guest:test.local")
    mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_invite_member_error_raises_room_error(setup_test_env):
    """RoomInviteError → RoomError, close() trotzdem aufgerufen."""
    inviter_tokens = _make_tokens("@inviter:test.local")
    invitee_tokens = _make_tokens("@guest:test.local")

    mock_client = _make_nio_client(
        room_invite_resp=_make_room_invite_error()
    )

    def ensure_identity_side_effect(uid):
        return inviter_tokens if uid == "inviter" else invitee_tokens

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import invite_member, RoomError
        with pytest.raises(RoomError):
            await invite_member("!room:test.local", "inviter", "guest")

    mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# list_members
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_members_returns_mxids(setup_test_env):
    """list_members gibt die MXIDs aus joined_members zurück."""
    requester_tokens = _make_tokens("@requester:test.local")
    mxids = ["@alice:test.local", "@bob:test.local", "@requester:test.local"]
    mock_client = _make_nio_client(
        joined_members_resp=_make_joined_members_response(mxids)
    )

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(return_value=requester_tokens),
        ),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import list_members
        result = await list_members("!room:test.local", "requester")

    assert sorted(result) == sorted(mxids)
    mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_members_error_raises_room_error(setup_test_env):
    """JoinedMembersError → RoomError, close() trotzdem aufgerufen."""
    requester_tokens = _make_tokens("@requester:test.local")
    mock_client = _make_nio_client(
        joined_members_resp=_make_joined_members_error()
    )

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(return_value=requester_tokens),
        ),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import list_members, RoomError
        with pytest.raises(RoomError):
            await list_members("!room:test.local", "requester")

    mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# list_rooms
# ---------------------------------------------------------------------------

def test_list_rooms_returns_db_rows(setup_test_env):
    """list_rooms gibt DB-Einträge zurück, kein Netzwerk."""
    from hydrahive.db import teamchat as db
    db.create_room("!r1:test.local", "Room One", "user1")
    db.create_room("!r2:test.local", "Room Two", "user2")

    from hydrahive.teamchat.rooms import list_rooms
    rows = list_rooms("user1")

    ids = [r["room_id"] for r in rows]
    assert "!r1:test.local" in ids
    assert "!r2:test.local" in ids
    assert len(rows) >= 2


def test_list_rooms_empty(setup_test_env):
    """list_rooms gibt leere Liste zurück wenn keine Räume vorhanden."""
    from hydrahive.teamchat.rooms import list_rooms
    rows = list_rooms("nobody")
    assert rows == []
