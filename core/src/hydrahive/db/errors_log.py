"""errors_log: zentrale Fehler-Persistenz (Token-Audit #129).

Erfasst Fehler die heute nur per `logger.exception()` in Datei-Logs gehen
und nach Logrotate verloren sind. Insbesondere:
- LLM-Call-Crashes (Runner)
- Background-Tasks (asyncio.create_task — schluckt Exceptions sonst)
- MCP/Plugin-Crashes mit Detail
- Mirror-Sync-Fehler

Verwendung:
    from hydrahive.db import errors_log
    errors_log.record(source="runner.llm_call", exc=e, session_id=sid, ...)

Oder als Context-Manager (re-raisst nach dem Logging):
    with errors_log.capture(source="my_op", session_id=sid):
        do_risky_thing()
"""
from __future__ import annotations

import contextlib
import json
import logging
import secrets
import traceback as tb_mod
from typing import Iterator

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)


def _new_id() -> str:
    return f"err_{secrets.token_hex(8)}"


def record(
    source: str,
    *,
    exc: BaseException | None = None,
    severity: str = "error",
    session_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    message: str | None = None,
    error_type: str | None = None,
    context: dict | None = None,
) -> str | None:
    """Schreibt einen Fehler-Eintrag. Returnt die ID oder None bei Crash.

    `exc` überschreibt error_type/message/traceback aus der Exception selbst,
    sofern nicht explizit übergeben.
    """
    eid = _new_id()
    try:
        if exc is not None:
            error_type = error_type or type(exc).__name__
            message = message or str(exc)
            tb_text = "".join(tb_mod.format_exception(type(exc), exc, exc.__traceback__))
        else:
            tb_text = None

        with db() as conn:
            conn.execute(
                """INSERT INTO errors_log
                   (id, created_at, session_id, agent_id, user_id,
                    source, severity, error_type, error_message, traceback, context)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    eid, now_iso(), session_id, agent_id, user_id,
                    source, severity, error_type, message, tb_text,
                    json.dumps(context) if context else None,
                ),
            )
        return eid
    except Exception:
        # errors_log darf selbst nicht crashen — sonst verlieren wir den Fehler
        # UND haben einen Folge-Fehler. Wir loggen nur, kein Re-Raise.
        logger.exception("errors_log.record fehlgeschlagen für source=%s", source)
        return None


@contextlib.contextmanager
def capture(
    source: str,
    *,
    severity: str = "error",
    session_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    context: dict | None = None,
    reraise: bool = True,
) -> Iterator[None]:
    """Context-Manager: fängt Exception, loggt nach errors_log, re-raisst (Default).

    Bei `reraise=False` wird die Exception geschluckt — nützlich für
    Background-Tasks bei denen Crashes sonst stillschweigend verloren gehen.
    """
    try:
        yield
    except Exception as e:
        record(
            source, exc=e, severity=severity,
            session_id=session_id, agent_id=agent_id, user_id=user_id,
            context=context,
        )
        if reraise:
            raise


def for_session(session_id: str) -> list[dict]:
    """Holt alle Fehler einer Session (Read-Path, primär für Debug/UI)."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM errors_log WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def recent(limit: int = 100, severity: str | None = None) -> list[dict]:
    """Holt die N letzten Fehler (für globales Debug-View)."""
    sql = "SELECT * FROM errors_log"
    params: tuple = ()
    if severity:
        sql += " WHERE severity = ?"
        params = (severity,)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params = params + (limit,)
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
