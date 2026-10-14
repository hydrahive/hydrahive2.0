"""Gemeinsamer Einstieg der vier Lösch-Routen (Spec archiv-system.md, Etappe 2).

`?mode=archive|permanent&confirm=<name>`:
- ohne mode → 409 delete_mode_required
- permanent und confirm ist nicht genau der Name → 400 delete_confirm_mismatch
- sonst 202 {"job_id": …}; das Löschen läuft als Auftrag im Hintergrund.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status
from fastapi.responses import JSONResponse

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.archive import jobs
from hydrahive.archive.deletion import MODES


def start(kind: str, target_id: str, name: str, mode: str | None, confirm: str | None, actor: str) -> JSONResponse:
    if not mode:
        raise coded(status.HTTP_409_CONFLICT, "delete_mode_required")
    if mode not in MODES:
        raise coded(status.HTTP_400_BAD_REQUEST, "delete_mode_invalid", mode=mode)
    if mode == "permanent" and confirm != name:
        raise coded(status.HTTP_400_BAD_REQUEST, "delete_confirm_mismatch")
    try:
        job_id = jobs.submit(kind, target_id, mode, actor=actor, name=name)
    except jobs.JobConflict:
        raise coded(status.HTTP_409_CONFLICT, "delete_in_progress")
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"job_id": job_id})


def delete_agent(agent_id: str, admin: Annotated[tuple[str, str], Depends(require_admin)],
                 mode: str | None = None, confirm: str | None = None) -> JSONResponse:
    """DELETE /api/agents/{id} – eingehängt in routes/agents.py."""
    try:
        agent = agent_config.get(agent_id)
    except ValueError:
        agent = None
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    return start("agent", agent_id, agent.get("name") or agent_id, mode, confirm, admin[0])
