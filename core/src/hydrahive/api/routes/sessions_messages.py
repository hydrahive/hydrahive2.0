from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import StreamingResponse

from hydrahive.agents import config as agent_config
from hydrahive.agents._paths import ensure_workspace
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._files import process_upload
from hydrahive.api.routes._sessions_helpers import check_owner, serialize_message
from hydrahive.api.routes._sse import to_sse
from hydrahive.compaction import compact_session, total_tokens
from hydrahive.compaction.compactor import DEFAULT_RESERVE_TOKENS
from hydrahive.compaction.tokens import context_window_for
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db import tools as tools_db
from hydrahive.runner import run as runner_run

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
    window = context_window_for(agent["llm_model"]) if agent else 0
    threshold = max(0, window - DEFAULT_RESERVE_TOKENS)
    return {
        "used": used,
        "context_window": window,
        "compact_threshold": threshold,
        "model": agent["llm_model"] if agent else None,
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
        return await compact_session(session_id, model=compact_model, **compact_kwargs)
    except Exception as e:
        raise coded(status.HTTP_500_INTERNAL_SERVER_ERROR, "validation_error", message=str(e))


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

    file_list = files or []
    if file_list:
        agent = agent_config.get(s.agent_id)
        workspace = ensure_workspace(agent) if agent else None
        blocks: list[dict] = []
        for f in file_list:
            blocks.extend(await process_upload(f, workspace))
        blocks.append({"type": "text", "text": text})
        user_content: str | list = blocks
    else:
        user_content = text

    events = runner_run(session_id, user_content)
    return StreamingResponse(
        to_sse(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
