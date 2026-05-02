from __future__ import annotations

from fastapi import UploadFile
from fastapi.responses import StreamingResponse

from hydrahive.agents import config as agent_config
from hydrahive.agents._paths import ensure_workspace
from hydrahive.api.routes._files import process_upload
from hydrahive.api.routes._sse import to_sse


async def build_user_content(agent_id: str, text: str, files: list[UploadFile]) -> str | list:
    if not files:
        return text
    agent = agent_config.get(agent_id)
    workspace = ensure_workspace(agent) if agent else None
    blocks: list[dict] = []
    for f in files:
        blocks.extend(await process_upload(f, workspace))
    blocks.append({"type": "text", "text": text})
    return blocks


def sse_run_response(events) -> StreamingResponse:
    return StreamingResponse(
        to_sse(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
