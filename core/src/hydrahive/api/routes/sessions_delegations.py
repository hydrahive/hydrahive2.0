"""Hintergrund-Aufträge einer Session: anzeigen, abbrechen, jetzt zustellen.

docs/specs/agent-background-delegation.md, Abschnitt „API“. Jeder Endpunkt
prüft den Besitzer der Session; eine Delegation muss zur Session gehören.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._sessions_helpers import check_owner
from hydrahive.db import delegations as delegations_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import concurrency, delegation_control, delegation_delivery

delegations_router = APIRouter()


def _session(session_id: str, auth: tuple[str, str]):
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    return s


@delegations_router.get("/{session_id}/delegations")
def list_delegations(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    s = _session(session_id, auth)
    rows = delegations_db.list_for_session(session_id)
    return {
        "delegations": [delegation_control.serialize(d, s.user_id) for d in rows],
        "undelivered": delegations_db.has_undelivered(session_id),
        "paused": delegation_delivery.is_paused(session_id),
    }


@delegations_router.post("/{session_id}/delegations/{delegation_id}/cancel")
def cancel_delegation(
    session_id: str,
    delegation_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    _session(session_id, auth)
    d = delegations_db.get(delegation_id)
    if not d or d["session_id"] != session_id:
        raise coded(status.HTTP_404_NOT_FOUND, "delegation_not_found")
    return {"cancelled": delegation_control.cancel(d)}


@delegations_router.post("/{session_id}/delegations/deliver")
async def deliver_now(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """„Jetzt auswerten“: wartende Ergebnisse sofort zustellen (auch nach Stopp)."""
    _session(session_id, auth)
    if concurrency.is_running(session_id):
        raise coded(status.HTTP_409_CONFLICT, "session_already_running")
    return {"started": delegation_delivery.kick(session_id, auto=False)}
