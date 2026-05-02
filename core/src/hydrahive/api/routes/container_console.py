"""WebSocket-Endpoint für die Container-Console.

Nachrichten-Format:
- Client → Server: Text-Frame (JSON `{"type":"input","data":"..."}` oder
  `{"type":"resize","rows":N,"cols":N}`).
- Server → Client: Binary-Frames mit den rohen PTY-Bytes (UTF-8/ANSI).

Auth via JWT im Query-Param `?token=...` (WS unterstützt keine
Authorization-Header in Browsern).
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import jwt
from hydrahive.api.middleware.auth import _decode
from hydrahive.containers import db as cdb
from hydrahive.containers.console import ConsoleSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["containers"])


def _authenticate(token: str | None) -> tuple[str, str] | None:
    if not token:
        return None
    try:
        payload = _decode(token)
    except (ValueError, KeyError, jwt.InvalidTokenError):
        return None
    return payload["sub"], payload["role"]


@router.websocket("/api/containers/{container_id}/console")
async def container_console(ws: WebSocket, container_id: str, token: str | None = None):
    auth = _authenticate(token)
    if not auth:
        await ws.close(code=4401)
        return
    user, role = auth

    c = cdb.get(container_id)
    if not c or (c.owner != user and role != "admin"):
        await ws.close(code=4404)
        return
    if c.actual_state != "running":
        await ws.close(code=4409)
        return

    await ws.accept()
    session = ConsoleSession(c.name)

    async def on_output(data: bytes) -> None:
        try:
            await ws.send_bytes(data)
        except Exception:  # WebSocket disconnected — all errors are expected here
            pass

    async def on_exit() -> None:
        try:
            await ws.close()
        except Exception:  # WebSocket may already be closed
            pass

    try:
        await session.start(on_output, on_exit)
    except RuntimeError as e:
        await ws.close(code=4500, reason=str(e))
        return

    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if "text" in msg and msg["text"]:
                try:
                    payload = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                kind = payload.get("type")
                if kind == "input":
                    data = payload.get("data", "")
                    if isinstance(data, str):
                        session.write(data.encode("utf-8", errors="replace"))
                elif kind == "resize":
                    rows = int(payload.get("rows", 24))
                    cols = int(payload.get("cols", 80))
                    session.resize(rows, cols)
            elif "bytes" in msg and msg["bytes"]:
                session.write(msg["bytes"])
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("Console-WS-Fehler: %s", e)
    finally:
        await session.stop()
