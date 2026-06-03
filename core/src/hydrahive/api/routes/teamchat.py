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
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_auth
from hydrahive.teamchat import messages, rooms
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
    user_id = auth[0]
    try:
        await rooms.invite_member(room_id, user_id, body.user_id)
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
