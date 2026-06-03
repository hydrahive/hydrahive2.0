"""agent_membership — Bot in Räume zu-/wegschalten (TDD).

Netzwerk gemockt (build_client liefert MagicMock-nio-Clients). DB gemockt.
Authz liegt in der Route, nicht hier — diese Tests prüfen nur die Mechanik.
"""
from __future__ import annotations

import nio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _bot_tokens(mxid="@agent-buddy:test.local"):
    from hydrahive.teamchat.client import AccountTokens
    return AccountTokens(user_id=mxid, access_token="bottok", device_id="BD")


def _user_tokens(mxid="@till:test.local"):
    from hydrahive.teamchat.client import AccountTokens
    return AccountTokens(user_id=mxid, access_token="usertok", device_id="UD")


def _client(*, invite=None, join=None, leave=None):
    c = MagicMock()
    c.room_invite = AsyncMock(return_value=invite)
    c.join = AsyncMock(return_value=join)
    c.room_leave = AsyncMock(return_value=leave)
    c.close = AsyncMock()
    return c


# ---------------------------------------------------------------- attach

@pytest.mark.asyncio
async def test_attach_invites_bot_joins_and_records():
    room_id = "!r:test.local"
    inviter_client = _client(invite=MagicMock(spec=nio.RoomInviteResponse))
    bot_client = _client(join=MagicMock(spec=nio.JoinResponse))
    db = MagicMock()
    with (
        patch("hydrahive.teamchat.agent_membership.ensure_bot_identity", new=AsyncMock(return_value=_bot_tokens())),
        patch("hydrahive.teamchat.agent_membership.ensure_identity", new=AsyncMock(return_value=_user_tokens())),
        patch("hydrahive.teamchat.agent_membership.build_client", side_effect=[inviter_client, bot_client]),
        patch("hydrahive.teamchat.agent_membership.db_teamchat", db),
    ):
        from hydrahive.teamchat.agent_membership import attach_agent
        await attach_agent(room_id, "till", "a1")

    inviter_client.room_invite.assert_awaited_once_with(room_id, "@agent-buddy:test.local")
    bot_client.join.assert_awaited_once_with(room_id)
    db.attach_agent.assert_called_once_with(room_id, "a1", "till")
    inviter_client.close.assert_awaited_once()
    bot_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_attach_tolerates_invite_failure_if_join_succeeds():
    """Bot evtl. schon Mitglied → Invite-Fehler egal, solange join klappt (idempotent)."""
    room_id = "!r:test.local"
    inviter_client = _client(invite=MagicMock(spec=nio.RoomInviteError))
    bot_client = _client(join=MagicMock(spec=nio.JoinResponse))
    db = MagicMock()
    with (
        patch("hydrahive.teamchat.agent_membership.ensure_bot_identity", new=AsyncMock(return_value=_bot_tokens())),
        patch("hydrahive.teamchat.agent_membership.ensure_identity", new=AsyncMock(return_value=_user_tokens())),
        patch("hydrahive.teamchat.agent_membership.build_client", side_effect=[inviter_client, bot_client]),
        patch("hydrahive.teamchat.agent_membership.db_teamchat", db),
    ):
        from hydrahive.teamchat.agent_membership import attach_agent
        await attach_agent(room_id, "till", "a1")

    db.attach_agent.assert_called_once_with(room_id, "a1", "till")


@pytest.mark.asyncio
async def test_attach_raises_when_join_fails():
    """Bot kann nicht beitreten → Fehler, KEIN DB-Eintrag (sonst Geister-Zuordnung)."""
    room_id = "!r:test.local"
    inviter_client = _client(invite=MagicMock(spec=nio.RoomInviteResponse))
    bot_client = _client(join=MagicMock(spec=nio.JoinError))
    db = MagicMock()
    with (
        patch("hydrahive.teamchat.agent_membership.ensure_bot_identity", new=AsyncMock(return_value=_bot_tokens())),
        patch("hydrahive.teamchat.agent_membership.ensure_identity", new=AsyncMock(return_value=_user_tokens())),
        patch("hydrahive.teamchat.agent_membership.build_client", side_effect=[inviter_client, bot_client]),
        patch("hydrahive.teamchat.agent_membership.db_teamchat", db),
    ):
        from hydrahive.teamchat.agent_membership import attach_agent, AgentMembershipError
        with pytest.raises(AgentMembershipError):
            await attach_agent(room_id, "till", "a1")

    db.attach_agent.assert_not_called()


# ---------------------------------------------------------------- detach

@pytest.mark.asyncio
async def test_detach_removes_record_and_bot_leaves():
    room_id = "!r:test.local"
    bot_client = _client(leave=MagicMock(spec=nio.RoomLeaveResponse))
    db = MagicMock()
    with (
        patch("hydrahive.teamchat.agent_membership.ensure_bot_identity", new=AsyncMock(return_value=_bot_tokens())),
        patch("hydrahive.teamchat.agent_membership.build_client", return_value=bot_client),
        patch("hydrahive.teamchat.agent_membership.db_teamchat", db),
    ):
        from hydrahive.teamchat.agent_membership import detach_agent
        await detach_agent(room_id, "a1")

    db.detach_agent.assert_called_once_with(room_id, "a1")
    bot_client.room_leave.assert_awaited_once_with(room_id)
    bot_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_detach_tolerates_leave_failure():
    """Bot schon weg → room_leave-Fehler darf detach nicht hochreißen (DB ist schon sauber)."""
    room_id = "!r:test.local"
    bot_client = _client(leave=MagicMock(spec=nio.RoomLeaveError))
    db = MagicMock()
    with (
        patch("hydrahive.teamchat.agent_membership.ensure_bot_identity", new=AsyncMock(return_value=_bot_tokens())),
        patch("hydrahive.teamchat.agent_membership.build_client", return_value=bot_client),
        patch("hydrahive.teamchat.agent_membership.db_teamchat", db),
    ):
        from hydrahive.teamchat.agent_membership import detach_agent
        await detach_agent(room_id, "a1")  # darf NICHT werfen

    db.detach_agent.assert_called_once_with(room_id, "a1")
