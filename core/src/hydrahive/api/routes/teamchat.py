"""Team-Chat HTTP-API — Rooms, Messages, Members, SSE-Stream.

Schicht-1: FastAPI-Router der teamchat/rooms.py, teamchat/messages.py und
teamchat/broadcaster.py zu REST-Endpoints verdrahtet. Die POST-Message-Route
broadcastet direkt nach dem Matrix-Send — kein separater Sync-Loop nötig.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware import users as hh_users
from hydrahive.api.middleware.auth import require_auth
from hydrahive.db import teamchat as db_teamchat
from hydrahive.teamchat import agent_bridge, agent_membership, messages, rooms
from hydrahive.teamchat.agent_membership import AgentMembershipError
from hydrahive.teamchat.broadcaster import room_broadcaster
from hydrahive.teamchat.messages import MessageError
from hydrahive.teamchat.rooms import RoomError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/teamchat", tags=["teamchat"])


# ---------------------------------------------------------------------------
# Availability guard
# ---------------------------------------------------------------------------

def _require_teamchat() -> None:
    """409 wenn teamchat nicht konfiguriert/eingeschaltet ist."""
    # Lazy import: verhindert settings.data_dir-Freeze bei Collection-Zeit
    from hydrahive.settings import settings

    if not settings.teamchat_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="teamchat_not_configured",
        )


_TC = Depends(_require_teamchat)


# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------

class CreateRoomBody(BaseModel):
    name: str
    members: list[str] = []


class SendMessageBody(BaseModel):
    text: str


class InviteMemberBody(BaseModel):
    user_id: str


class AttachAgentBody(BaseModel):
    agent_id: str


class RenameRoomBody(BaseModel):
    name: str = Field(min_length=1, max_length=255)


# ---------------------------------------------------------------------------
# Authz helpers (Agent-Endpoints schreiben in die HH-DB → nicht Matrix-geschützt)
# ---------------------------------------------------------------------------

async def _require_member(room_id: str, user_id: str) -> None:
    """403 wenn der User kein Mitglied des Raums ist."""
    try:
        member = await rooms.is_member(room_id, user_id)
    except RoomError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if not member:
        raise HTTPException(status_code=403, detail="not_a_member")


def _require_agent_owner(agent_id: str, user_id: str, role: str) -> dict:
    """404 wenn der Agent fehlt, 403 wenn der User ihn nicht besitzt (Admin darf)."""
    cfg = agent_config.get(agent_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="agent_not_found")
    if role != "admin" and cfg.get("owner") != user_id:
        raise HTTPException(status_code=403, detail="not_your_agent")
    return cfg


def _require_room_manager(room_id: str, user_id: str, role: str) -> dict:
    """404 wenn Raum unbekannt, 403 wenn User weder Ersteller noch Admin ist.

    Mitglieder hinzufügen/entfernen darf nur, wer den Raum erstellt hat (er hat
    auch das Matrix-Power-Level) — oder ein Admin.
    """
    room = db_teamchat.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room_not_found")
    if role != "admin" and room.get("created_by") != user_id:
        raise HTTPException(status_code=403, detail="not_room_manager")
    return room


def _require_known_user(user_id: str) -> None:
    """404 wenn der User kein registrierter HH-User ist — verhindert, dass ein
    Tippfehler beim Einladen einen Geister-Matrix-Account provisioniert."""
    if not any(u.get("username") == user_id for u in hh_users.list_users()):
        raise HTTPException(status_code=404, detail="user_not_found")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/rooms", dependencies=[_TC])
async def get_rooms(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    user_id = auth[0]
    try:
        return await rooms.list_joined_rooms(user_id)
    except RoomError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/rooms", status_code=status.HTTP_201_CREATED, dependencies=[_TC])
async def post_rooms(
    body: CreateRoomBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user_id = auth[0]
    try:
        room_id = await rooms.create_room(user_id, body.name, body.members)
    except RoomError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"room_id": room_id}


@router.patch(
    "/rooms/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_TC],
)
async def patch_room(
    room_id: str,
    body: RenameRoomBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    user_id, role = auth
    _require_room_manager(room_id, user_id, role)
    try:
        await rooms.rename_room(room_id, user_id, body.name)
    except RoomError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.delete(
    "/rooms/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_TC],
)
async def delete_room(
    room_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    user_id, role = auth
    _require_room_manager(room_id, user_id, role)
    try:
        await rooms.delete_room(room_id, user_id)
    except RoomError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/rooms/{room_id}/messages", dependencies=[_TC])
async def get_messages(
    room_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    user_id = auth[0]
    try:
        return await messages.history(room_id, user_id, limit)
    except MessageError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/rooms/{room_id}/messages", dependencies=[_TC])
async def post_message(
    room_id: str,
    body: SendMessageBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user_id = auth[0]
    try:
        result = await messages.send_message(room_id, user_id, body.text)
    except MessageError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    # Broadcast to all SSE subscribers of this room (Schicht-1: POST-side broadcast)
    room_broadcaster.broadcast(room_id, json.dumps(result))
    # Zugeschaltete Agenten bei Anrede antworten lassen — fire-and-forget,
    # damit die HTTP-Antwort nicht auf den Agent-Run wartet.
    # Schicht-1: Anrede-Erkennung nur über den Text (@name / Vokativ). Das
    # explizite m.mentions-Signal (is_addressed kann es) wird in Etappe 4b vom
    # Frontend geliefert und hier als mention_mxids durchgereicht.
    agent_bridge.schedule_response(room_id, user_id, body.text)
    return result


@router.get("/rooms/{room_id}/members", dependencies=[_TC])
async def get_members(
    room_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[str]:
    user_id = auth[0]
    try:
        return await rooms.list_members(room_id, user_id)
    except RoomError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post(
    "/rooms/{room_id}/members",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_TC],
)
async def post_members(
    room_id: str,
    body: InviteMemberBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    user_id, role = auth
    room = _require_room_manager(room_id, user_id, role)
    _require_known_user(body.user_id)
    try:
        # Als Raum-Ersteller einladen — er hat das Matrix-Power-Level (greift auch
        # wenn ein Admin einlädt, der den Raum nicht erstellt hat).
        await rooms.invite_member(room_id, room["created_by"], body.user_id)
    except RoomError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.delete(
    "/rooms/{room_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_TC],
)
async def delete_member(
    room_id: str,
    user_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    requester, role = auth
    room = _require_room_manager(room_id, requester, role)
    if user_id == room["created_by"]:
        # Den Ersteller zu kicken würde den Raum unbedienbar machen (Power-Level weg).
        raise HTTPException(status_code=422, detail="cannot_remove_room_owner")
    try:
        # Kick als Ersteller ausführen (Power-Level), nicht als Requester.
        await rooms.kick_member(room_id, room["created_by"], user_id)
    except RoomError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/rooms/{room_id}/stream", dependencies=[_TC])
async def stream_room(
    room_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> StreamingResponse:
    """SSE-Kanal für Live-Updates in einem Room.

    Broadcast kommt von post_message (POST /rooms/{id}/messages). Keepalive
    alle 20s als SSE-Kommentar, damit Proxies die Verbindung nicht killen.
    Membership-Check via Matrix joined_rooms — Nicht-Mitglieder erhalten 403.
    """
    user_id = auth[0]
    try:
        member = await rooms.is_member(room_id, user_id)
    except RoomError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if not member:
        raise HTTPException(status_code=403, detail="not_a_member")

    queue = room_broadcaster.subscribe(room_id)

    async def _events():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            room_broadcaster.unsubscribe(room_id, queue)

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Agent-Zuschaltung
# ---------------------------------------------------------------------------

@router.get("/rooms/{room_id}/agents", dependencies=[_TC])
async def get_room_agents(
    room_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    await _require_member(room_id, auth[0])
    result: list[dict] = []
    for entry in db_teamchat.list_room_agents(room_id):
        cfg = agent_config.get(entry["agent_id"])
        result.append({
            "agent_id": entry["agent_id"],
            "name": cfg.get("name") if cfg else None,
        })
    return result


@router.post(
    "/rooms/{room_id}/agents",
    status_code=status.HTTP_201_CREATED,
    dependencies=[_TC],
)
async def post_room_agent(
    room_id: str,
    body: AttachAgentBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user_id, role = auth
    await _require_member(room_id, user_id)
    _require_agent_owner(body.agent_id, user_id, role)
    try:
        await agent_membership.attach_agent(room_id, user_id, body.agent_id)
    except AgentMembershipError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"room_id": room_id, "agent_id": body.agent_id}


@router.delete(
    "/rooms/{room_id}/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_TC],
)
async def delete_room_agent(
    room_id: str,
    agent_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    user_id, role = auth
    await _require_member(room_id, user_id)
    _require_agent_owner(agent_id, user_id, role)
    await agent_membership.detach_agent(room_id, agent_id)
