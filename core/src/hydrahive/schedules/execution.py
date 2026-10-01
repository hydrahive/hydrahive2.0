"""Execute one claimed scheduled task."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from hydrahive.agents import config as agent_config
from hydrahive.buddy import get_or_create_buddy
from hydrahive.butler import executor as butler_executor
from hydrahive.api.routes._session_access import assert_agent_access, assert_project_access
from hydrahive.butler._scheduled_agent_run import (
    _AGENT_ID_RE, _owner_role, run_scheduled_agent_actions,
)
from hydrahive.butler.models import TriggerEvent
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner
from hydrahive.runner.events import Done, Error
from hydrahive.schedules import db
from hydrahive.schedules.models import ScheduledTask

logger = logging.getLogger(__name__)
_RUN_TIMEOUT_SECONDS = 15 * 60


async def _run_butler_task(task: ScheduledTask, run_id: str) -> None:
    event = TriggerEvent(
        event_type="schedule",
        owner=task.owner,
        payload={
            "schedule_id": task.task_id,
            "task_id": task.task_id,
            "agent_id": task.target_id,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    results = await butler_executor.dispatch_event(event, owner=task.owner)
    session_ids: list[str] = []
    errors: list[str] = []
    for result in results:
        try:
            outcome = await run_scheduled_agent_actions(
                owner=result["owner"],
                flow_id=result["flow_id"],
                flow_name=result["flow_name"],
                project_id=result.get("project_id"),
                event=event,
                actions=result["actions_executed"],
            )
        except Exception as exc:
            logger.warning(
                "Scheduled Butler-Flow %s fehlgeschlagen: %s",
                result["flow_id"], exc,
            )
            errors.append(f"{result['flow_id']}: {exc}")
            continue
        session_ids.extend(outcome.session_ids)
        errors.extend(outcome.errors)
    session_id = session_ids[-1] if session_ids else None
    if errors:
        db.finish(
            task.task_id,
            run_id,
            status="failed",
            session_id=session_id,
            error="; ".join(errors)[:2000],
        )
    else:
        kwargs = {"session_id": session_id} if session_id else {}
        db.finish(task.task_id, run_id, status="succeeded", **kwargs)


def _authorize_direct(task: ScheduledTask, target_id: str) -> str | None:
    """Rechte bei JEDER Ausführung prüfen, nicht nur beim Anlegen (zweite
    Sicherheitsprüfung 01.10.2026): entzogene Projektmitgliedschaft oder ein
    inzwischen fremder Agent stoppen die Aufgabe. Liefert die Fehlermeldung."""
    if not _AGENT_ID_RE.fullmatch(target_id or ""):
        return "Ungültige Agent-ID"
    agent = agent_config.get(target_id)
    if not agent or agent.get("id") != target_id:
        return f"Ziel-Agent nicht gefunden: {target_id}"
    role = _owner_role(task.owner)
    project = None
    if task.project_id:
        try:
            project = assert_project_access(task.project_id, task.owner, role)
        except HTTPException:
            return f"Projektzugriff für {task.project_id} nicht mehr erlaubt"
    try:
        assert_agent_access(agent, project, task.owner, role)
    except HTTPException:
        return f"Kein Zugriff auf Agent {target_id}"
    return None


async def _run_direct_task(task: ScheduledTask, run_id: str) -> None:
    target_id = task.target_id
    if task.target_type == "buddy":
        state = get_or_create_buddy(task.owner)
        target_id = state["agent_id"]
    refused = _authorize_direct(task, target_id)
    if refused:
        logger.warning("Intervallaufgabe %s/%s startet nicht: %s", task.owner, task.task_id, refused)
        db.finish(task.task_id, run_id, status="failed", error=refused)
        return
    session = sessions_db.create(
        agent_id=target_id,
        user_id=task.owner,
        project_id=task.project_id,
        title=f"Automatisch: {task.title}",
        metadata={"scheduled_task_id": task.task_id},
    )
    final_error: str | None = None
    async for event in runner.run(session.id, task.prompt):
        if isinstance(event, Error):
            final_error = event.message
        elif isinstance(event, Done):
            final_error = None
    if final_error:
        db.finish(
            task.task_id,
            run_id,
            status="failed",
            session_id=session.id,
            error=final_error,
        )
    else:
        db.finish(task.task_id, run_id, status="succeeded", session_id=session.id)


async def _execute_task(task: ScheduledTask, run_id: str) -> None:
    if task.execution_mode == "butler_event":
        await _run_butler_task(task, run_id)
    else:
        await _run_direct_task(task, run_id)


async def run_task(task: ScheduledTask, run_id: str) -> None:
    try:
        await asyncio.wait_for(
            _execute_task(task, run_id), timeout=_RUN_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        message = f"Zeitlimit von {_RUN_TIMEOUT_SECONDS:g} Sekunden überschritten"
        logger.error("Scheduled task %s abgebrochen: %s", task.task_id, message)
        db.finish(task.task_id, run_id, status="failed", error=message)
    except asyncio.CancelledError:
        db.finish(task.task_id, run_id, status="failed", error="Ausführung abgebrochen")
        raise
    except Exception as exc:
        logger.exception("Scheduled task %s fehlgeschlagen", task.task_id)
        db.finish(task.task_id, run_id, status="failed", error=str(exc)[:2000])
