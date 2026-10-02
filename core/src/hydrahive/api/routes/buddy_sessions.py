"""Buddy: frühere Unterhaltungen auflisten und wieder öffnen.

Spec docs/specs/buddy-session-picker.md. Nur eigene Web-Sitzungen des eigenen
Buddy; Kanal-Sitzungen (WhatsApp, Discord …) bleiben außen vor.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.buddy import sessions_picker

router = APIRouter(prefix="/api/buddy/sessions", tags=["buddy"])


@router.get("")
def list_buddy_sessions(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> dict:
    try:
        return sessions_picker.list_sessions(auth[0], offset=offset, limit=limit)
    except LookupError:
        raise coded(status.HTTP_404_NOT_FOUND, "buddy_not_found")


@router.post("/{session_id}/open")
def open_buddy_session(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    try:
        return sessions_picker.open_session(auth[0], session_id)
    except sessions_picker.RunActive:
        raise coded(status.HTTP_409_CONFLICT, "session_already_running")
    except LookupError:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
