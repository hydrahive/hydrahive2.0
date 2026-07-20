from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status

logger = logging.getLogger(__name__)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api._session_broadcast import broadcaster
from hydrahive.api.routes._session_msg_helpers import build_user_content, sse_run_with_guard
from hydrahive.runner import run as runner_run
from hydrahive.runner.concurrency import SessionAlreadyRunning, is_running, session_run_guard
from hydrahive.runner.events import Error as RunnerError
from hydrahive.api.routes._sessions_helpers import check_owner, serialize_message
from hydrahive.agents._defaults import DEFAULT_COMPACT_THRESHOLD_PCT
from hydrahive.compaction import (
    compact_session,
    compact_threshold_tokens,
    default_max_turns,
    total_tokens,
)
from hydrahive.compaction.tokens import context_window_for
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db import tools as tools_db

messages_router = APIRouter()


@messages_router.get("/{session_id}/messages")
def list_messages(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    msgs = messages_db.list_for_session(session_id)
    # tool_calls.duration_ms in tool_use- und tool_result-Blocks einspielen.
    # tool_calls.id ≠ tool_use.id (verschiedene Namespaces) — wir mappen über
    # die Reihenfolge: tools_db.list_for_message liefert in created_at-ASC,
    # gleicher Order wie tool_use-Blocks in der Assistant-Message.
    durations: dict[str, int] = {}
    for m in msgs:
        if m.role != "assistant" or not isinstance(m.content, list):
            continue
        tool_uses = [b for b in m.content if isinstance(b, dict) and b.get("type") == "tool_use"]
        tcs = tools_db.list_for_message(m.id)
        for tu, tc in zip(tool_uses, tcs):
            if tc.duration_ms is not None and tu.get("id"):
                durations[tu["id"]] = tc.duration_ms
    return [serialize_message(m, durations) for m in msgs]


@messages_router.get("/{session_id}/stream")
async def stream_session(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> StreamingResponse:
    """Live-Sync v1: SSE-Kanal, den jedes offene Gerät derselben Session abonniert.

    Während ein Lauf läuft (egal von welchem Gerät ausgelöst) broadcastet die
    Sende-Route leichte Pings hier rein; der Client lädt bei Ping nach. Keepalive
    alle 20s als SSE-Kommentar, damit Proxies die Verbindung nicht killen.
    """
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)

    queue = broadcaster.subscribe(session_id)

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
            broadcaster.unsubscribe(session_id, queue)

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@messages_router.get("/{session_id}/tokens")
def get_tokens(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    agent = agent_config.get(s.agent_id)
    history = messages_db.list_for_llm(session_id) if agent else []
    used = total_tokens(history)
    model = ((s.metadata or {}).get("model_override") or agent["llm_model"]) if agent else ""
    window = context_window_for(model) if agent else 0
    threshold = (
        compact_threshold_tokens(
            model,
            threshold_pct=int(agent.get("compact_threshold_pct", DEFAULT_COMPACT_THRESHOLD_PCT)),
            reserve_tokens=agent.get("compact_reserve_tokens"),
        )
        if agent
        else 0
    )
    # Turn-Netz sichtbar machen: Compaction feuert auch bei message_count >=
    # max_turns (window-skaliert), nicht nur an der Token-Schwelle. Ohne diese
    # Zahl wirkt ein turn-getriggerter Compact „verfrüht" (Balken steht < 100%).
    max_turns = (
        (agent.get("compact_max_turns") or default_max_turns(model))
        if agent
        else 0
    )
    return {
        "used": used,
        "context_window": window,
        "compact_threshold": threshold,
        "model": agent["llm_model"] if agent else None,
        "message_count": len(history),
        "max_turns": max_turns,
    }


@messages_router.post("/{session_id}/compact")
async def manual_compact(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    instructions: str | None = None,
) -> dict:
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    agent = agent_config.get(s.agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    compact_model = agent.get("compact_model") or agent["llm_model"]
    compact_kwargs: dict = {"instructions": instructions}
    tool_limit = agent.get("compact_tool_result_limit")
    if tool_limit is not None:
        compact_kwargs["tool_result_limit"] = tool_limit
    try:
        return await compact_session(
            session_id, model=compact_model,
            triggered_by="manual", **compact_kwargs,
        )
    except Exception as e:
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "validation_error", message=str(e))


@messages_router.post("/{session_id}/messages/{message_id}/resend")
async def resend_message(
    session_id: str,
    message_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    text: Annotated[str, Form(min_length=1)],
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> StreamingResponse:
    """Edit + Resend: Schneidet die History ab `message_id` (inklusive) ab
    und schreibt eine neue User-Message mit `text`. Triggered den Runner
    wie bei einer normalen post_message."""
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)

    target = messages_db.get(message_id)
    if not target or target.session_id != session_id:
        raise coded(status.HTTP_404_NOT_FOUND, "message_not_found")
    if target.role != "user":
        raise coded(status.HTTP_400_BAD_REQUEST, "message_not_editable")

    user_content = await build_user_content(s, text, files or [])
    messages_db.delete_from(session_id, message_id)
    return await sse_run_with_guard(session_id, user_content)


@messages_router.post("/{session_id}/messages")
async def post_message(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    text: Annotated[str, Form(min_length=1)],
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> StreamingResponse:
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)

    user_content = await build_user_content(s, text, files or [])
    return await sse_run_with_guard(session_id, user_content)


class LogCmdBody(BaseModel):
    user_text: str = Field(min_length=1, max_length=2000)
    assistant_text: str = Field(min_length=1, max_length=8000)


@messages_router.post("/{session_id}/log-cmd")
async def log_slash_cmd(
    session_id: str,
    body: LogCmdBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Slash-Command-Output dauerhaft als Messages in die Session schreiben.

    Spiegelt /api/buddy/log-cmd, aber für beliebige Sessions. Kein LLM-Roundtrip,
    nur DB-Append: User-Text als user-msg, deterministischer Output als
    assistant-msg mit metadata.source='slash_command'.
    """
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    user_msg = messages_db.append(session_id, "user", body.user_text)
    asst_msg = messages_db.append(
        session_id, "assistant",
        [{"type": "text", "text": body.assistant_text}],
        metadata={"source": "slash_command"},
    )
    return {"ok": True, "user_id": user_msg.id, "assistant_id": asst_msg.id}


@messages_router.post("/{session_id}/inject", dependencies=[Depends(require_admin)])
async def inject_message(
    session_id: str,
    text: Annotated[str, Form(min_length=1)],
    background_tasks: BackgroundTasks,
) -> dict:
    """Supervisor-Inject: Admin schickt eine Nachricht in eine fremde Session.

    Kein Owner-Check — nur Admins. Startet den Runner als Background-Task und
    gibt sofort {"accepted": true} zurück, damit der Client nicht auf den
    SSE-Stream warten muss (fire-and-forget für MCP/Monitoring-Agents).
    """
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    if is_running(session_id):
        raise coded(status.HTTP_409_CONFLICT, "session_already_running")
    user_content = await build_user_content(s, text, [])

    async def _run() -> None:
        logger.info("inject %s: background task starting", session_id)
        try:
            async with session_run_guard(session_id):
                async for event in runner_run(session_id, user_content):
                    if isinstance(event, RunnerError):
                        logger.error("inject %s: runner yielded error: %s", session_id, event)
        except SessionAlreadyRunning:
            logger.info("inject %s: session already running, skipped", session_id)
        except Exception:
            logger.exception("inject %s: runner error", session_id)
        logger.info("inject %s: background task done", session_id)

    background_tasks.add_task(_run)
    return {"accepted": True, "session_id": session_id}


class LogIngestBody(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str | list
    message_id: str | None = None
    token_count: int | None = None
    created_at: str | None = None
    metadata: dict | None = None


@messages_router.post("/{session_id}/log")
async def log_ingest(
    session_id: str,
    body: LogIngestBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Externer Live-Ingest: hängt eine Message an und löst den Mirror aus.

    Reines Mitschreiben — kein Agenten-Lauf (vgl. /inject). Idempotent über
    body.message_id (INSERT OR IGNORE). Für externe Claude-Code-Instanzen, die
    ihre Konversation ins Datamining spiegeln.

    MUSS async sein: mirror.schedule_message() nutzt asyncio.get_running_loop().
    Als sync def liefe der Endpoint im Threadpool ohne Loop → der Mirror-Task
    würde still verworfen und nur SQLite bekäme die Message (Datamining bliebe leer).
    """
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    if body.created_at is not None:
        try:
            datetime.fromisoformat(body.created_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_timestamp")
    existed = bool(body.message_id) and messages_db.get(body.message_id) is not None
    m = messages_db.append(
        session_id,
        body.role,
        body.content,
        token_count=body.token_count,
        metadata=body.metadata,
        message_id=body.message_id,
        created_at=body.created_at,
    )
    return {"ok": True, "message_id": m.id, "inserted": not existed}
