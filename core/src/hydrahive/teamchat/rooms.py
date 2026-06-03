"""teamchat/rooms.py — Matrix room management for HydraHive team-chat.

Free-form rooms (Slack-channel style, not project-bound).
Composes ensure_identity, build_client, and db.teamchat.
"""
from __future__ import annotations

import logging

import nio

from hydrahive.db import teamchat as db_teamchat
from hydrahive.teamchat.client import build_client
from hydrahive.teamchat.identity import ensure_identity

logger = logging.getLogger(__name__)


class RoomError(Exception):
    """Raised when a Matrix room operation fails."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_room(
    creator_user_id: str,
    name: str,
    invite_user_ids: list[str],
) -> str:
    """Create a Matrix room and persist it in the DB.

    1. Ensure Matrix identity for creator and all invitees.
    2. Create room via nio with preset=private_chat.
    3. Store room in DB.
    4. Return Matrix room_id.
    """
    # Lazy import avoids settings.data_dir freeze at collection time
    from hydrahive.settings import settings

    creator = await ensure_identity(creator_user_id)

    # Provision all invitees so their accounts exist before invite
    invitee_mxids: list[str] = []
    for uid in invite_user_ids:
        tokens = await ensure_identity(uid)
        invitee_mxids.append(tokens.user_id)

    client = build_client(
        settings.matrix_homeserver_url,
        creator.user_id,
        creator.access_token,
        creator.device_id,
    )
    try:
        resp = await client.room_create(
            name=name,
            preset=nio.RoomPreset.private_chat,
            invite=invitee_mxids,
        )
        if not isinstance(resp, nio.RoomCreateResponse):
            raise RoomError(f"room_create failed: {resp!r}")
        room_id = resp.room_id
    finally:
        await client.close()

    db_teamchat.create_room(room_id, name, creator_user_id)
    logger.info(
        "create_room: room=%s name=%r creator=%s invitees=%s",
        room_id, name, creator_user_id, invitee_mxids,
    )
    return room_id


async def invite_member(
    room_id: str,
    inviter_user_id: str,
    invitee_user_id: str,
) -> None:
    """Invite a HydraHive user to an existing Matrix room."""
    from hydrahive.settings import settings

    inviter = await ensure_identity(inviter_user_id)
    invitee = await ensure_identity(invitee_user_id)

    client = build_client(
        settings.matrix_homeserver_url,
        inviter.user_id,
        inviter.access_token,
        inviter.device_id,
    )
    try:
        resp = await client.room_invite(room_id, invitee.user_id)
        if not isinstance(resp, nio.RoomInviteResponse):
            raise RoomError(f"room_invite failed: {resp!r}")
    finally:
        await client.close()

    logger.info(
        "invite_member: room=%s inviter=%s invitee=%s",
        room_id, inviter_user_id, invitee_user_id,
    )


async def list_members(room_id: str, requester_user_id: str) -> list[str]:
    """Return a list of MXIDs of joined members in a room."""
    from hydrahive.settings import settings

    requester = await ensure_identity(requester_user_id)

    client = build_client(
        settings.matrix_homeserver_url,
        requester.user_id,
        requester.access_token,
        requester.device_id,
    )
    try:
        resp = await client.joined_members(room_id)
        if not isinstance(resp, nio.JoinedMembersResponse):
            raise RoomError(f"joined_members failed: {resp!r}")
        return [m.user_id for m in resp.members]
    finally:
        await client.close()


async def list_joined_rooms(user_id: str) -> list[dict]:
    """Return DB metadata only for rooms the user is actually joined to in Matrix.

    Calls client.joined_rooms() — the authoritative membership source — then
    intersects with teamchat_rooms in our DB.  Rooms that exist in Matrix but
    not in our DB (foreign rooms) are silently skipped.
    """
    from hydrahive.settings import settings

    u = await ensure_identity(user_id)
    client = build_client(
        settings.matrix_homeserver_url,
        u.user_id,
        u.access_token,
        u.device_id,
    )
    try:
        resp = await client.joined_rooms()
        if not isinstance(resp, nio.JoinedRoomsResponse):
            raise RoomError(f"joined_rooms failed: {resp!r}")
    finally:
        await client.close()

    return [
        row
        for rid in resp.rooms
        if (row := db_teamchat.get_room(rid)) is not None
    ]


async def is_member(room_id: str, user_id: str) -> bool:
    """Return True if user_id is currently joined to room_id in Matrix."""
    from hydrahive.settings import settings

    u = await ensure_identity(user_id)
    client = build_client(
        settings.matrix_homeserver_url,
        u.user_id,
        u.access_token,
        u.device_id,
    )
    try:
        resp = await client.joined_rooms()
        if not isinstance(resp, nio.JoinedRoomsResponse):
            raise RoomError(f"joined_rooms failed: {resp!r}")
        return room_id in resp.rooms
    finally:
        await client.close()
