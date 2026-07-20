from __future__ import annotations

import shutil
import time
from uuid import uuid4

from fastapi import UploadFile, status
from fastapi.responses import StreamingResponse

from hydrahive.agents import config as agent_config
from hydrahive.api._session_broadcast import broadcaster
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._files import (
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_MESSAGE_UPLOAD_BYTES,
    UploadSizeUnknown,
    UploadTooLarge,
    UploadTooManyFiles,
    process_upload,
    validate_upload_sizes,
)
from hydrahive.api.routes._sse import to_sse
from hydrahive.runner import run as runner_run
from hydrahive.runner._run_workspace import resolve_run_context
from hydrahive.runner.concurrency import SessionAlreadyRunning, is_running, session_run_guard

# Live-Sync v1: max ein Aktivitäts-Ping pro Intervall während eines Laufs.
_PING_INTERVAL_S = 0.5


async def build_user_content(session, text: str, files: list[UploadFile]) -> str | list:
    if not files:
        return text
    agent = agent_config.get(session.agent_id)
    workspace = resolve_run_context(session, agent)[0] if agent else None
    upload_dir = (
        workspace / ".hydrahive" / "uploads" / uuid4().hex
        if workspace is not None else None
    )
    try:
        validate_upload_sizes(files)
        blocks: list[dict] = []
        for file in files:
            blocks.extend(await process_upload(file, upload_dir))
    except (UploadSizeUnknown, UploadTooLarge, UploadTooManyFiles) as exc:
        _cleanup_upload_batch(upload_dir)
        raise _upload_http_error(exc)
    except Exception:
        _cleanup_upload_batch(upload_dir)
        raise
    blocks.append({"type": "text", "text": text})
    return blocks


def _cleanup_upload_batch(upload_dir) -> None:
    if upload_dir is not None:
        shutil.rmtree(upload_dir, ignore_errors=True)


def _upload_http_error(exc):
    if isinstance(exc, UploadTooLarge):
        if exc.scope == "message":
            return coded(
                status.HTTP_413_CONTENT_TOO_LARGE,
                "upload_total_too_large",
                max_mib=MAX_MESSAGE_UPLOAD_BYTES // (1024 * 1024),
            )
        return coded(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "upload_file_too_large",
            filename=exc.filename or "upload",
            max_mib=MAX_FILE_BYTES // (1024 * 1024),
        )
    if isinstance(exc, UploadTooManyFiles):
        return coded(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "upload_too_many_files",
            max_files=MAX_FILES,
        )
    return coded(status.HTTP_400_BAD_REQUEST, "upload_size_unknown")


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


async def sse_run_with_guard(session_id: str, user_content, *, extra_system: str | None = None) -> StreamingResponse:
    """SSE-Response für runner_run MIT Session-Concurrency-Guard.

    409 wenn für die Session bereits ein Run läuft. Verhindert dass
    bei abgerissenem SSE-Stream (Browser-Refresh, Modell-Switch, Network-Hiccup)
    ein zweiter Run parallel angestoßen wird — siehe runner.concurrency
    für den Hintergrund.
    """
    if is_running(session_id):
        raise coded(status.HTTP_409_CONFLICT, "session_already_running")

    async def _guarded_stream():
        # Live-Sync v1: leichte Pings an alle Geräte derselben Session, damit ein
        # passives Tab/Tablet bei Lauf-Fortschritt nachlädt. Der Sender-Stream
        # (yield ev) bleibt davon unberührt.
        last_ping = 0.0
        try:
            async with session_run_guard(session_id):
                broadcaster.broadcast(session_id, '{"t":"start"}')
                if extra_system is not None:
                    gen = runner_run(session_id, user_content, extra_system=extra_system)
                else:
                    gen = runner_run(session_id, user_content)
                async for ev in gen:
                    yield ev
                    now = time.monotonic()
                    if now - last_ping >= _PING_INTERVAL_S:
                        last_ping = now
                        broadcaster.broadcast(session_id, '{"t":"activity"}')
        except SessionAlreadyRunning:
            return  # lost the race between is_running() check and acquire
        finally:
            broadcaster.broadcast(session_id, '{"t":"done"}')

    return sse_run_response(_guarded_stream())
