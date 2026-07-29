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
from hydrahive.api.routes._sse import encode_event, to_sse
from hydrahive.runner.events import Error as RunnerError
import asyncio
import logging

from hydrahive.runner import run as runner_run
from hydrahive.runner._run_workspace import resolve_run_context
from hydrahive.runner.concurrency import (
    SessionAlreadyRunning,
    is_running,
    register_task,
    session_run_guard,
    unregister_task,
)
from hydrahive.runner.event_bus import bus as event_bus

logger = logging.getLogger(__name__)

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


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def sse_run_response(events) -> StreamingResponse:
    return StreamingResponse(
        to_sse(events),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


async def _raw_with_heartbeat(frames):
    """Reicht bereits SSE-serialisierte Frames (aus dem Event-Bus) durch und
    fügt bei Inaktivität einen Heartbeat-Comment ein, damit Proxies/Browser die
    Verbindung nicht schließen."""
    it = frames.__aiter__()
    task: asyncio.Task | None = None
    try:
        while True:
            if task is None:
                task = asyncio.ensure_future(it.__anext__())
            done, _ = await asyncio.wait({task}, timeout=15)
            if not done:
                yield ": heartbeat\n\n"
                continue
            task = None
            try:
                yield done.pop().result()
            except StopAsyncIteration:
                break
    finally:
        if task is not None:
            task.cancel()


def sse_run_response_raw(frames) -> StreamingResponse:
    return StreamingResponse(
        _raw_with_heartbeat(frames),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


def start_run_task(session_id: str, user_content, *, extra_system: str | None = None) -> "asyncio.Task":
    """Startet einen Agent-Run als ENTKOPPELTEN Server-Task.

    Der Run hängt NICHT an der auslösenden HTTP-Verbindung — schließt der Browser
    (oder geht der PC aus), läuft der Run serverseitig zu Ende. Über
    concurrency.cancel(session_id) (Stop-Button → POST /stop) lässt er sich
    jederzeit gezielt abbrechen, auch nach einem Reconnect.

    Variante A: Läuft bereits ein Run für die Session → SessionAlreadyRunning
    (kein Doppellauf, schützt lange Läufe). Der Aufrufer übersetzt das in 409.

    Live-Fortschritt geht wie bisher über den broadcaster (start/activity/done);
    die Clients laden bei Ping aus der DB nach.
    """
    if is_running(session_id):
        raise SessionAlreadyRunning(session_id)

    # Frischen Event-Bus-Kanal öffnen (seq startet bei 0), BEVOR der erste
    # Consumer (der Sende-Stream) subscribed — kein Event geht verloren.
    event_bus.open(session_id)

    async def _run() -> None:
        last_ping = 0.0
        try:
            async with session_run_guard(session_id):
                broadcaster.broadcast(session_id, '{"t":"start"}')
                if extra_system is not None:
                    gen = runner_run(session_id, user_content, extra_system=extra_system)
                else:
                    gen = runner_run(session_id, user_content)
                async for ev in gen:
                    # Volles Event in den Bus (flüssiges Token-Streaming für ALLE
                    # Consumer, auch nach Reconnect lückenlos).
                    event_bus.publish(session_id, encode_event(ev))
                    now = time.monotonic()
                    if now - last_ping >= _PING_INTERVAL_S:
                        last_ping = now
                        # Leichter Ping für passive Tabs (die aus der DB nachladen).
                        broadcaster.broadcast(session_id, '{"t":"activity"}')
        except SessionAlreadyRunning:
            return  # Race verloren — anderer Task hält den Guard
        except asyncio.CancelledError:
            logger.info("Run gestoppt (cancel): %s", session_id)
            event_bus.publish(session_id, encode_event(
                RunnerError(message="Lauf gestoppt.")))
            raise
        except Exception:
            logger.exception("Entkoppelter Run fehlgeschlagen: %s", session_id)
        finally:
            unregister_task(session_id)
            event_bus.close(session_id)
            broadcaster.broadcast(session_id, '{"t":"done"}')

    task = asyncio.create_task(_run())
    register_task(session_id, task)
    return task


async def run_and_stream(session_id: str, user_content, *, extra_system: str | None = None) -> StreamingResponse:
    """Startet den entkoppelten Run und gibt einen SSE-Stream zurück, der die
    Events aus dem Event-Bus liest. Reißt DIESER Stream ab (Browser zu), läuft
    der Run weiter — er hängt am Server-Task, nicht an der Verbindung.

    409 wenn schon ein Run läuft (Variante A: kein Doppellauf)."""
    start_run_task(session_id, user_content, extra_system=extra_system)  # wirft SessionAlreadyRunning → vom Router in 409 übersetzt

    async def _events():
        async for _seq, sse_frame in event_bus.subscribe(session_id, after_seq=0):
            yield sse_frame  # bereits SSE-serialisiert (encode_event)

    return sse_run_response_raw(_events())


async def attach_stream(session_id: str, after_seq: int = 0) -> StreamingResponse:
    """Zuschauer-/Reconnect-Stream: liest denselben Event-Bus ab `after_seq`.
    Läuft kein Run, endet der Stream schnell (leerer Kanal). Für den Stop-Button
    nach Reconnect zählt der running-Status (siehe /stop + is_running)."""
    async def _events():
        async for _seq, sse_frame in event_bus.subscribe(session_id, after_seq=after_seq):
            yield sse_frame

    return sse_run_response_raw(_events())



