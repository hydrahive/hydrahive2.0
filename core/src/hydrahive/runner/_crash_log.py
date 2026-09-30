"""Tool-Abstürze nach errors_log schreiben (Task ff8644b2).

Tool-, MCP- und Plugin-Abstürze gingen bisher nur per logger.exception ins
Journal. Die Ursache von 184 shell_exec-Abstürzen blieb dadurch monatelang
unentdeckt. Hier landet jeder Absturz zusätzlich in errors_log, mit Tool-Name,
Verweis auf den tool_calls-Eintrag und Traceback.

Meldung, Traceback und Kontext werden mit denselben Secret-Werten geschwärzt
wie der Tool-Output im Dispatcher. Ein Absturz im Tool kann ein Secret in der
Exception-Meldung oder in den Argumenten tragen.

Die Quellen enden auf „.crash“. Die Dashboard-Kachel „Heute Fehler“ zieht sie
ab, weil derselbe Absturz schon als fehlgeschlagener tool_call zählt.
"""
from __future__ import annotations

import logging
import traceback as tb_mod

from hydrahive.credentials import redaction
from hydrahive.db import errors_log
from hydrahive.tools.base import ToolContext

logger = logging.getLogger(__name__)


def crash_secrets(ctx: ToolContext) -> set[str]:
    """Dieselbe Secret-Menge wie an der Engstelle im Dispatcher."""
    return (redaction.secret_values() | redaction.agent_secret_values(ctx.agent_id)
            | redaction.user_secret_values(ctx.user_id))


def record_crash(source: str, tool_name: str, exc: BaseException, ctx: ToolContext,
                 *, tool_call_id: str | None = None) -> None:
    """Schreibt einen geschwärzten errors_log-Eintrag. Wirft nie."""
    try:
        secrets = crash_secrets(ctx)
        tb_text = "".join(tb_mod.format_exception(type(exc), exc, exc.__traceback__))
        context = {"tool": tool_name}
        if tool_call_id:
            context["tool_call_id"] = tool_call_id
        errors_log.record(
            source,
            error_type=type(exc).__name__,
            message=redaction.scrub(str(exc), secrets),
            traceback=redaction.scrub(tb_text, secrets),
            session_id=ctx.session_id, agent_id=ctx.agent_id, user_id=ctx.user_id,
            context=redaction.scrub(context, secrets),
        )
    except Exception:
        # Der Absturz selbst ist schon im Journal (logger.exception beim Aufrufer).
        logger.exception("Tool-Absturz konnte nicht nach errors_log geschrieben werden")
