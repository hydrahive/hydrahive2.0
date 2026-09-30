"""Abgefangene Tool-Fehler mit Ursache melden (Task a0a8486d).

Viele Tools fangen `except Exception as e` und meldeten nur str(e). Bei
TimeoutError ist das leer: datamining_search meldete 55-mal nur
„Datamining-Suche fehlgeschlagen:“, ohne jede Ursache.

fail_with_cause() nennt immer den Fehlertyp, bei Zeitüberschreitung im
Klartext, und hängt einen optionalen Hinweis an. Der Traceback geht ins Log.

Bewusst KEIN errors_log: Das sind erwartete, abgefangene Tool-Fehler
(Datei gesperrt, SMTP lehnt ab), die schon als fehlgeschlagener tool_call
gespeichert sind. errors_log bleibt für echte Abstürze (runner/_crash_log.py).
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.tools.base import ToolResult

logger = logging.getLogger(__name__)

_TIMEOUTS = (TimeoutError, asyncio.TimeoutError)


def describe(exc: BaseException) -> str:
    """„Typ: Text“, „Typ“ bei leerem Text, Zeitüberschreitung im Klartext."""
    name = type(exc).__name__
    if isinstance(exc, _TIMEOUTS):
        return f"Zeitüberschreitung ({name})"
    text = str(exc).strip()
    return f"{name}: {text}" if text else name


def fail_with_cause(prefix: str, exc: BaseException, tool: str, *, hint: str | None = None) -> ToolResult:
    logger.warning("Tool '%s': %s", tool, prefix, exc_info=exc)
    message = f"{prefix}: {describe(exc)}"
    if hint and isinstance(exc, _TIMEOUTS):
        message += f". {hint}"
    return ToolResult.fail(message)
