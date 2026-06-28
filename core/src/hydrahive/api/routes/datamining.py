from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Annotated, Any

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.db import mirror, mirror_query

router = APIRouter(prefix="/api/datamining", tags=["datamining"])

Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.get("/events")
async def get_recent_events(_auth: Auth, limit: int = 100) -> dict:
    events = await mirror.recent_events(min(limit, 500))
    return {"active": mirror._pool is not None, "events": events}


@router.get("/search")
async def search_events(
    _auth: Auth,
    q: str = Query(default=""),
    event_type: str | None = None,
    agent_name: str | None = None,
    username: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    semantic: bool = False,
    limit: int = 20,
) -> dict:
    active = mirror._pool is not None
    if not active:
        return {"active": False, "results": [], "error": None}
    try:
        results = await mirror_query.search_events(
            q,
            event_type=event_type or None,
            agent_name=agent_name or None,
            username=username or None,
            from_date=from_date or None,
            to_date=to_date or None,
            semantic=semantic,
            limit=min(limit, 100),
        )
        return {"active": True, "results": results, "error": None}
    except Exception as e:
        logger.warning("search_events fehlgeschlagen: %s", e)
        return {"active": True, "results": [], "error": str(e)}


@router.get("/sessions")
async def list_sessions(
    _auth: Auth,
    agent_name: str | None = None,
    username: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 50,
) -> dict:
    active = mirror._pool is not None
    if not active:
        return {"active": False, "sessions": []}
    sessions = await mirror_query.list_sessions(
        agent_name=agent_name or None,
        username=username or None,
        from_date=from_date or None,
        to_date=to_date or None,
        limit=min(limit, 500),
    )
    return {"active": True, "sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, _auth: Auth) -> dict:
    detail = await mirror_query.get_session_detail(session_id)
    if detail is None:
        raise HTTPException(404, "Session nicht gefunden")
    return detail


@router.get("/graph")
async def get_graph(_auth: Auth) -> dict:
    from hydrahive.db.mirror_graph_topology import build_topology
    return await build_topology()


@router.get("/embed/status")
async def get_embed_status(_auth: Auth) -> dict:
    return await mirror_query.embed_status()


@router.post("/embed/reset")
async def reset_embeddings(_auth: Auth, event_type: str | None = None) -> dict:
    count = await mirror.reset_embeddings(event_type)
    return {"ok": True, "reset": count}


@router.post("/embed/rechunk")
async def rechunk_events(_auth: Auth) -> dict:
    """Schneidet alle tool_result-Events die länger als CHUNK_CHARS sind neu."""
    if mirror._pool is None:
        return {"ok": False, "reason": "Mirror nicht aktiv"}
    from hydrahive.api.routes._datamining_rechunk import run_rechunk
    asyncio.get_running_loop().create_task(run_rechunk())
    return {"ok": True, "message": "Rechunk gestartet — läuft im Hintergrund"}


@router.post("/embed/backfill")
async def trigger_backfill(_auth: Auth) -> dict:
    from hydrahive.llm._config import load_config
    if mirror._pool is None:
        return {"ok": False, "reason": "Mirror nicht aktiv"}
    if mirror._backfill_running:
        return {"ok": False, "reason": "Backfill läuft bereits"}
    model = load_config().get("embed_model", "")
    if not model:
        return {"ok": False, "reason": "Kein Embedding-Modell konfiguriert"}
    mirror._backfill_task = asyncio.get_running_loop().create_task(mirror._run_backfill(model))
    return {"ok": True, "model": model}


class _IngestEvent(BaseModel):
    id: str
    message_id: str
    session_id: str
    block_index: int = 0
    event_type: str
    created_at: str
    username: str | None = None
    agent_name: str | None = None
    text: str | None = None
    tool_name: str | None = None
    tool_use_id: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: str | None = None
    is_error: bool = False


class _IngestRequest(BaseModel):
    events: list[_IngestEvent]


def _dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@router.post("/ingest", dependencies=[Depends(require_admin)])
async def ingest_transcript(body: _IngestRequest) -> dict:
    """Nimmt geparste Claude-Code-Session-Events und schreibt sie in die Mirror-DB."""
    if mirror._pool is None:
        raise HTTPException(503, "Mirror nicht aktiv")
    if not body.events:
        return {"ok": True, "inserted": 0}

    rows = [
        (e.id, e.message_id, e.session_id, e.block_index, 0, 1,
         e.event_type, _dt(e.created_at), e.username, e.agent_name,
         e.text, e.tool_name, e.tool_use_id,
         json.dumps(e.tool_input) if e.tool_input else None,
         e.tool_output, e.is_error)
        for e in body.events
    ]
    async with mirror._pool.acquire() as conn:
        await conn.executemany("""
            INSERT INTO events (id, message_id, session_id, block_index, chunk_index, chunk_total,
                               event_type, created_at, username, agent_name, text,
                               tool_name, tool_use_id, tool_input, tool_output, is_error)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14::jsonb,$15,$16)
            ON CONFLICT (id) DO NOTHING
        """, rows)
    return {"ok": True, "inserted": len(rows)}


@router.post("/import/sqlite")
async def start_sqlite_import(_auth: Auth) -> dict:
    from hydrahive.db.mirror_import_sqlite import run_sqlite_import, sqlite_import_status
    s = sqlite_import_status()
    if s["running"]:
        return {"ok": False, "reason": "Import läuft bereits"}
    asyncio.get_running_loop().create_task(run_sqlite_import())
    return {"ok": True}


@router.get("/import/sqlite/status")
async def get_sqlite_import_status(_auth: Auth) -> dict:
    from hydrahive.db.mirror_import_sqlite import sqlite_import_status
    return sqlite_import_status()


@router.post("/import/git")
async def start_git_import(_auth: Auth, repo_path: str = "") -> dict:
    from hydrahive.db.mirror_import_git import run_git_import, git_import_status
    from hydrahive.settings import settings
    s = git_import_status()
    if s["running"]:
        return {"ok": False, "reason": "Import läuft bereits"}
    path = repo_path or str(settings.repo_dir if hasattr(settings, "repo_dir") else settings.hh_repo_dir)
    asyncio.get_running_loop().create_task(run_git_import(path))
    return {"ok": True, "repo": path}


@router.get("/import/git/status")
async def get_git_import_status(_auth: Auth) -> dict:
    from hydrahive.db.mirror_import_git import git_import_status
    return git_import_status()


@router.post("/import/jsonl")
async def start_jsonl_import(_auth: Auth) -> dict:
    from hydrahive.db.mirror_import_jsonl import run_jsonl_import, jsonl_import_status
    s = jsonl_import_status()
    if s["running"]:
        return {"ok": False, "reason": "Import läuft bereits"}
    asyncio.get_running_loop().create_task(run_jsonl_import())
    return {"ok": True}


@router.get("/import/jsonl/status")
async def get_jsonl_import_status(_auth: Auth) -> dict:
    from hydrahive.db.mirror_import_jsonl import jsonl_import_status
    return jsonl_import_status()


@router.post("/import/logs")
async def start_logs_import(
    _auth: Auth,
    nginx_log: str = "/var/log/nginx/access.log",
    journal_unit: str = "hydrahive2",
    journal_lines: int = 5000,
) -> dict:
    from hydrahive.db.mirror_import_logs import run_logs_import, logs_import_status
    s = logs_import_status()
    if s["running"]:
        return {"ok": False, "reason": "Import läuft bereits"}
    asyncio.get_running_loop().create_task(run_logs_import(nginx_log, journal_unit, journal_lines))
    return {"ok": True}


@router.get("/import/logs/status")
async def get_logs_import_status(_auth: Auth) -> dict:
    from hydrahive.db.mirror_import_logs import logs_import_status
    return logs_import_status()


@router.post("/import/shell-history")
async def import_shell_history(
    _auth: Auth,
    file: UploadFile = File(...),
    username: str = "unknown",
) -> dict:
    if mirror._pool is None:
        return {"ok": False, "reason": "Mirror nicht aktiv"}
    content = (await file.read()).decode("utf-8", errors="replace")
    if not content.strip():
        return {"ok": True, "inserted": 0}
    from hydrahive.db.mirror_import_shell import run_shell_import
    return await run_shell_import(content, username)
