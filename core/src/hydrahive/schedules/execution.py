"""Execute one claimed scheduled task."""
from __future__ import annotations

import asyncio
import logging

from hydrahive.agents import config as agent_config
from hydrahive.buddy import get_or_create_buddy
from hydrahive.butler import executor as butler_executor
from hydrahive.butler.models import TriggerEvent
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner
from hydrahive.runner.events import Done, Error
from hydrahive.schedules import db
from hydrahive.schedules.models import ScheduledTask

logger = logging.getLogger(__name__)


async def run_task(task: ScheduledTask, run_id: str) -> None:
    try:
        if task.execution_mode == "butler_event":
            await butler_executor.dispatch_event(
                TriggerEvent(
                    event_type="schedule",
                    owner=task.owner,
                    payload={"schedule_id": task.task_id, "task_id": task.task_id,
                             "agent_id": task.target_id},
                ),
                owner=task.owner,
            )
            db.finish(task.task_id, run_id, status="succeeded")
            return

        target_id = task.target_id
        if task.target_type == "buddy":
            state = get_or_create_buddy(task.owner)
            target_id = state["agent_id"]
        agent = agent_config.get(target_id)
        if not agent:
            raise RuntimeError(f"Ziel-Agent nicht gefunden: {target_id}")
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
            db.finish(task.task_id, run_id, status="failed", session_id=session.id, error=final_error)
        else:
            db.finish(task.task_id, run_id, status="succeeded", session_id=session.id)
    except asyncio.CancelledError:
        db.finish(task.task_id, run_id, status="failed", error="Ausführung abgebrochen")
        raise
    except Exception as exc:
        logger.exception("Scheduled task %s fehlgeschlagen", task.task_id)
        db.finish(task.task_id, run_id, status="failed", error=str(exc)[:2000])
