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


def _make_join_response():
    import nio
    return MagicMock(spec=nio.JoinResponse)


def _make_join_error():
    import nio
    return MagicMock(spec=nio.JoinError)


def _make_nio_client(
    room_create_resp=None,
    room_invite_resp=None,
    joined_members_resp=None,
    join_resp=None,
):
    """Build a MagicMock nio.AsyncClient with AsyncMock methods."""
    if join_resp is None:
        join_resp = _make_join_response()
    mock_client = MagicMock()
    mock_client.room_create = AsyncMock(return_value=room_create_resp)
    mock_client.room_invite = AsyncMock(return_value=room_invite_resp)
    mock_client.joined_members = AsyncMock(return_value=joined_members_resp)
    mock_client.join = AsyncMock(return_value=join_resp)
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
    # build_client wird 2x aufgerufen: creator (room_create) + alice (join)
    creator_client = _make_nio_client(room_create_resp=_make_room_create_response(room_id))
    invitee_client = _make_nio_client()

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
            side_effect=[creator_client, invitee_client],
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
    # build_client 3x: creator (room_create) + alice (join) + bob (join)
    creator_client = _make_nio_client(room_create_resp=_make_room_create_response(room_id))
    alice_client = _make_nio_client()
    bob_client = _make_nio_client()

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
        patch(
            "hydrahive.teamchat.rooms.build_client",
            side_effect=[creator_client, alice_client, bob_client],
        ),
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
    creator_client = _make_nio_client(room_create_resp=_make_room_create_response(room_id))
    invitee_client = _make_nio_client()

    def ensure_identity_side_effect(uid):
        return creator_tokens if uid == "creator" else alice_tokens

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch(
            "hydrahive.teamchat.rooms.build_client",
            side_effect=[creator_client, invitee_client],
        ),
    ):
        from hydrahive.teamchat.rooms import create_room
        await create_room("creator", "My Room", ["alice"])

    creator_client.room_create.assert_awaited_once()
    kwargs = creator_client.room_create.call_args.kwargs
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
    """close() wird für den Creator-Client aufgerufen — auch ohne invitees."""
    creator_tokens = _make_tokens("@creator:test.local")
    room_id = "!closetest:test.local"
    # Keine invitees → build_client nur 1x aufgerufen
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
    """invite_member: room_invite + join aufgerufen, kein Fehler."""
    inviter_tokens = _make_tokens("@inviter:test.local")
    invitee_tokens = _make_tokens("@guest:test.local")

    # build_client 2x: inviter (room_invite) + invitee (join)
    inviter_client = _make_nio_client(room_invite_resp=_make_room_invite_response())
    invitee_client = _make_nio_client()

    def ensure_identity_side_effect(uid):
        return inviter_tokens if uid == "inviter" else invitee_tokens

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch(
            "hydrahive.teamchat.rooms.build_client",
            side_effect=[inviter_client, invitee_client],
        ),
    ):
        from hydrahive.teamchat.rooms import invite_member
        await invite_member("!room:test.local", "inviter", "guest")

    inviter_client.room_invite.assert_awaited_once_with("!room:test.local", "@guest:test.local")
    invitee_client.join.assert_awaited_once_with("!room:test.local")
    inviter_client.close.assert_awaited_once()
    invitee_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# kick_member — Mitglied entfernen (5a)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kick_member_success(setup_test_env, monkeypatch):
    """kick_member: room_kick auf die aus server_name gebaute Target-MXID
    (KEIN ensure_identity(target) → kein Geister-Account)."""
    import nio
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    kicker = _make_tokens("@admin:test.local")
    client = MagicMock()
    client.room_kick = AsyncMock(return_value=MagicMock(spec=nio.RoomKickResponse))
    client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=kicker)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=client),
    ):
        from hydrahive.teamchat.rooms import kick_member
        await kick_member("!room:test.local", "admin", "bibi")

    client.room_kick.assert_awaited_once_with("!room:test.local", "@bibi:test.local")
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_kick_member_error_raises(setup_test_env, monkeypatch):
    """room_kick-Fehler → RoomError, Client trotzdem geschlossen."""
    import nio
    monkeypatch.setenv("HH_MATRIX_SERVER_NAME", "test.local")
    kicker = _make_tokens("@admin:test.local")
    client = MagicMock()
    client.room_kick = AsyncMock(return_value=MagicMock(spec=nio.RoomKickError))
    client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=kicker)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=client),
    ):
        from hydrahive.teamchat.rooms import kick_member, RoomError
        with pytest.raises(RoomError):
            await kick_member("!room:test.local", "admin", "bibi")

    client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# rename_room / delete_room (5b)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rename_room_updates_db_and_matrix(setup_test_env, monkeypatch):
    """rename_room: DB-Name (HH-Quelle) + best-effort Matrix-Raumname."""
    import nio
    renamer = _make_tokens("@admin:test.local")
    client = MagicMock()
    client.room_put_state = AsyncMock(return_value=MagicMock(spec=nio.RoomPutStateResponse))
    client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=renamer)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=client),
        patch("hydrahive.teamchat.rooms.db_teamchat") as db_mock,
    ):
        from hydrahive.teamchat.rooms import rename_room
        await rename_room("!room:test.local", "admin", "Neuer Name")

    db_mock.update_room_name.assert_called_once_with("!room:test.local", "Neuer Name")
    client.room_put_state.assert_awaited_once()
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_rename_room_db_gewinnt_auch_wenn_matrix_scheitert(setup_test_env):
    """Matrix-Name-Setzen scheitert → DB-Rename trotzdem durchgeführt (HH-Truth)."""
    import nio
    renamer = _make_tokens("@admin:test.local")
    client = MagicMock()
    client.room_put_state = AsyncMock(return_value=MagicMock(spec=nio.RoomPutStateError))
    client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=renamer)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=client),
        patch("hydrahive.teamchat.rooms.db_teamchat") as db_mock,
    ):
        from hydrahive.teamchat.rooms import rename_room
        await rename_room("!room:test.local", "admin", "Trotzdem")  # darf NICHT werfen

    db_mock.update_room_name.assert_called_once_with("!room:test.local", "Trotzdem")
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_room_leaves_and_deletes(setup_test_env):
    """delete_room: Ersteller verlässt Matrix-Raum (best-effort) + DB-Löschung."""
    import nio
    deleter = _make_tokens("@admin:test.local")
    client = MagicMock()
    client.room_leave = AsyncMock(return_value=MagicMock(spec=nio.RoomLeaveResponse))
    client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=deleter)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=client),
        patch("hydrahive.teamchat.rooms.db_teamchat") as db_mock,
    ):
        from hydrahive.teamchat.rooms import delete_room
        await delete_room("!room:test.local", "admin")

    db_mock.delete_room.assert_called_once_with("!room:test.local")
    client.room_leave.assert_awaited_once_with("!room:test.local")
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_invite_member_error_raises_room_error(setup_test_env):
    """RoomInviteError → RoomError, close() trotzdem aufgerufen."""
    inviter_tokens = _make_tokens("@inviter:test.local")
    invitee_tokens = _make_tokens("@guest:test.local")

    # room_invite schlägt fehl → nur 1 build_client (inviter); invitee-join nie erreicht
    inviter_client = _make_nio_client(room_invite_resp=_make_room_invite_error())

    def ensure_identity_side_effect(uid):
        return inviter_tokens if uid == "inviter" else invitee_tokens

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch(
            "hydrahive.teamchat.rooms.build_client",
            return_value=inviter_client,
        ),
    ):
        from hydrahive.teamchat.rooms import invite_member, RoomError
        with pytest.raises(RoomError):
            await invite_member("!room:test.local", "inviter", "guest")

    inviter_client.close.assert_awaited_once()


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
# list_joined_rooms
# ---------------------------------------------------------------------------

def _make_joined_rooms_response(room_ids: list[str]):
    """Minimal nio.JoinedRoomsResponse mock."""
    import nio
    resp = MagicMock(spec=nio.JoinedRoomsResponse)
    resp.rooms = room_ids
    return resp


def _make_joined_rooms_error():
    import nio
    return MagicMock(spec=nio.JoinedRoomsError)


@pytest.mark.asyncio
async def test_list_joined_rooms_returns_only_joined_teamchat_rooms(setup_test_env):
    """list_joined_rooms gibt nur Räume zurück, in denen der User Mitglied ist
    UND die in der teamchat_rooms-DB vorhanden sind."""
    from hydrahive.db import teamchat as db
    db.create_room("!joined:test.local", "Joined Room", "user1")
    db.create_room("!other:test.local", "Other Room", "user2")

    tokens = _make_tokens("@user1:test.local")
    # User ist nur in !joined:test.local, nicht in !other:test.local
    mock_client = MagicMock()
    mock_client.joined_rooms = AsyncMock(
        return_value=_make_joined_rooms_response(["!joined:test.local", "!foreign:matrix.org"])
    )
    mock_client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=tokens)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import list_joined_rooms
        result = await list_joined_rooms("user1")

    ids = [r["room_id"] for r in result]
    assert "!joined:test.local" in ids
    assert "!other:test.local" not in ids   # user nicht Mitglied
    assert "!foreign:matrix.org" not in ids  # nicht in teamchat-DB
    mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_joined_rooms_empty_when_no_joined_rooms(setup_test_env):
    """Keine Matrix-Mitgliedschaften → leere Liste."""
    tokens = _make_tokens("@user1:test.local")
    mock_client = MagicMock()
    mock_client.joined_rooms = AsyncMock(
        return_value=_make_joined_rooms_response([])
    )
    mock_client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=tokens)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import list_joined_rooms
        result = await list_joined_rooms("user1")

    assert result == []
    mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_joined_rooms_raises_room_error_on_matrix_error(setup_test_env):
    """JoinedRoomsError → RoomError, close() trotzdem aufgerufen."""
    tokens = _make_tokens("@user1:test.local")
    mock_client = MagicMock()
    mock_client.joined_rooms = AsyncMock(
        return_value=_make_joined_rooms_error()
    )
    mock_client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=tokens)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import list_joined_rooms, RoomError
        with pytest.raises(RoomError):
            await list_joined_rooms("user1")

    mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# is_member
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_is_member_returns_true_when_room_in_joined_rooms(setup_test_env):
    """is_member gibt True zurück wenn room_id in joined_rooms-Response."""
    tokens = _make_tokens("@user1:test.local")
    mock_client = MagicMock()
    mock_client.joined_rooms = AsyncMock(
        return_value=_make_joined_rooms_response(["!target:test.local", "!other:test.local"])
    )
    mock_client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=tokens)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import is_member
        result = await is_member("!target:test.local", "user1")

    assert result is True
    mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_member_returns_false_when_room_not_in_joined_rooms(setup_test_env):
    """is_member gibt False zurück wenn room_id NICHT in joined_rooms-Response."""
    tokens = _make_tokens("@user1:test.local")
    mock_client = MagicMock()
    mock_client.joined_rooms = AsyncMock(
        return_value=_make_joined_rooms_response(["!other:test.local"])
    )
    mock_client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=tokens)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import is_member
        result = await is_member("!target:test.local", "user1")

    assert result is False
    mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_member_raises_room_error_on_matrix_error(setup_test_env):
    """JoinedRoomsError → RoomError, close() trotzdem aufgerufen."""
    tokens = _make_tokens("@user1:test.local")
    mock_client = MagicMock()
    mock_client.joined_rooms = AsyncMock(
        return_value=_make_joined_rooms_error()
    )
    mock_client.close = AsyncMock()

    with (
        patch("hydrahive.teamchat.rooms.ensure_identity", new=AsyncMock(return_value=tokens)),
        patch("hydrahive.teamchat.rooms.build_client", return_value=mock_client),
    ):
        from hydrahive.teamchat.rooms import is_member, RoomError
        with pytest.raises(RoomError):
            await is_member("!target:test.local", "user1")


# ---------------------------------------------------------------------------
# create_room — auto-join invitees
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_room_invitees_auto_join(setup_test_env):
    """Jeder invitee joinet den Raum automatisch nach room_create."""
    creator_tokens = _make_tokens("@creator:test.local")
    alice_tokens = _make_tokens("@alice:test.local", "tok_alice")
    bob_tokens = _make_tokens("@bob:test.local", "tok_bob")

    room_id = "!autojoin:test.local"
    creator_client = _make_nio_client(room_create_resp=_make_room_create_response(room_id))
    alice_client = _make_nio_client()
    bob_client = _make_nio_client()

    def ensure_identity_side_effect(uid):
        mapping = {"creator": creator_tokens, "alice": alice_tokens, "bob": bob_tokens}
        return mapping[uid]

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch(
            "hydrahive.teamchat.rooms.build_client",
            side_effect=[creator_client, alice_client, bob_client],
        ),
    ):
        from hydrahive.teamchat.rooms import create_room
        result = await create_room("creator", "Auto Join Room", ["alice", "bob"])

    assert result == room_id
    alice_client.join.assert_awaited_once_with(room_id)
    bob_client.join.assert_awaited_once_with(room_id)
    # Creator joinet nicht explizit (Matrix auto-join beim room_create)
    creator_client.join.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_room_join_error_logs_warning_does_not_raise(setup_test_env):
    """JoinError für einen invitee → warning geloggt, kein raise, room_id zurückgegeben."""
    creator_tokens = _make_tokens("@creator:test.local")
    alice_tokens = _make_tokens("@alice:test.local")

    room_id = "!joinfail:test.local"
    creator_client = _make_nio_client(room_create_resp=_make_room_create_response(room_id))
    # alice's join schlägt fehl
    alice_client = _make_nio_client(join_resp=_make_join_error())

    def ensure_identity_side_effect(uid):
        return creator_tokens if uid == "creator" else alice_tokens

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch(
            "hydrahive.teamchat.rooms.build_client",
            side_effect=[creator_client, alice_client],
        ),
        patch("hydrahive.teamchat.rooms.logger") as mock_logger,
    ):
        from hydrahive.teamchat.rooms import create_room
        result = await create_room("creator", "Join Fail Room", ["alice"])

    # Kein raise — room_id trotzdem zurückgegeben
    assert result == room_id
    # Warnung geloggt
    mock_logger.warning.assert_called()
    # Raum in DB persistiert
    from hydrahive.db import teamchat as db
    assert db.get_room(room_id) is not None
    # Client immer geschlossen
    alice_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_room_no_invitees_no_join_calls(setup_test_env):
    """Ohne invitees wird join nie aufgerufen."""
    creator_tokens = _make_tokens("@creator:test.local")
    room_id = "!noinvite:test.local"
    creator_client = _make_nio_client(room_create_resp=_make_room_create_response(room_id))

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(return_value=creator_tokens),
        ),
        patch(
            "hydrahive.teamchat.rooms.build_client",
            return_value=creator_client,
        ),
    ):
        from hydrahive.teamchat.rooms import create_room
        result = await create_room("creator", "No Invite Room", [])

    assert result == room_id
    creator_client.join.assert_not_awaited()


# ---------------------------------------------------------------------------
# invite_member — auto-join after invite
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invite_member_invitee_joins_after_invite(setup_test_env):
    """Nach room_invite joinet der invitee den Raum automatisch."""
    inviter_tokens = _make_tokens("@inviter:test.local")
    invitee_tokens = _make_tokens("@guest:test.local")

    inviter_client = _make_nio_client(room_invite_resp=_make_room_invite_response())
    invitee_client = _make_nio_client()

    def ensure_identity_side_effect(uid):
        return inviter_tokens if uid == "inviter" else invitee_tokens

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch(
            "hydrahive.teamchat.rooms.build_client",
            side_effect=[inviter_client, invitee_client],
        ),
    ):
        from hydrahive.teamchat.rooms import invite_member
        await invite_member("!room:test.local", "inviter", "guest")

    invitee_client.join.assert_awaited_once_with("!room:test.local")
    invitee_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_invite_member_join_error_raises_room_error(setup_test_env):
    """JoinError beim invitee-join → RoomError (invite_member muss den einen User wirklich einjoinen)."""
    inviter_tokens = _make_tokens("@inviter:test.local")
    invitee_tokens = _make_tokens("@guest:test.local")

    inviter_client = _make_nio_client(room_invite_resp=_make_room_invite_response())
    invitee_client = _make_nio_client(join_resp=_make_join_error())

    def ensure_identity_side_effect(uid):
        return inviter_tokens if uid == "inviter" else invitee_tokens

    with (
        patch(
            "hydrahive.teamchat.rooms.ensure_identity",
            new=AsyncMock(side_effect=ensure_identity_side_effect),
        ),
        patch(
            "hydrahive.teamchat.rooms.build_client",
            side_effect=[inviter_client, invitee_client],
        ),
    ):
        from hydrahive.teamchat.rooms import invite_member, RoomError
        with pytest.raises(RoomError):
            await invite_member("!room:test.local", "inviter", "guest")

    invitee_client.close.assert_awaited_once()
