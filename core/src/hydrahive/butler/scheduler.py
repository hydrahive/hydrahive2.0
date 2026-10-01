"""Zeitgesteuerter Butler-Cron-Emitter mit entkoppelten Flow-Läufen."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from croniter import croniter

from hydrahive.butler import executor as bex
from hydrahive.butler import persistence as bp
from hydrahive.butler._scheduled_agent_run import run_scheduled_agent_actions
from hydrahive.butler.models import Flow, Node, TriggerEvent

logger = logging.getLogger(__name__)

_STARTUP_DELAY = 20.0
_TICK_INTERVAL = 60.0
_MAX_FIRINGS_PER_TICK = 100
_RUN_TIMEOUT_SECONDS = 15 * 60
_RUNNING: dict[tuple[str, str], asyncio.Task[None]] = {}


def _cron_trigger(flow: Flow) -> Node | None:
    for node in flow.nodes:
        if node.type == "trigger" and node.subtype == "cron_fired":
            return node
    return None


def _fire_times(cron_expr: str, since: datetime, now: datetime) -> list[datetime]:
    """Cron-Zeitpunkte im Fenster (since, now]. Höchstens _MAX_FIRINGS_PER_TICK,
    und zwar die NEUESTEN: verpasste Läufe werden ohnehin zu einem
    zusammengefasst, der zählt mit dem jüngsten Zeitpunkt."""
    # get_prev liefert nur Zeitpunkte VOR dem Start — eine Sekunde später
    # anfangen, damit ein Zeitpunkt genau auf `now` mitzählt (Fenster inkl. now).
    times: list[datetime] = []
    iterator = croniter(cron_expr, now + timedelta(seconds=1))
    for _ in range(_MAX_FIRINGS_PER_TICK):
        prev = iterator.get_prev(datetime)
        if prev.tzinfo is None:
            prev = prev.replace(tzinfo=timezone.utc)
        if prev <= since:
            break
        times.append(prev)
    return sorted(times)


async def _execute_flow(flow: Flow, event: TriggerEvent, fired_at: datetime) -> None:
    result = await bex.dispatch(flow, event)
    outcome = await run_scheduled_agent_actions(
        owner=flow.owner,
        flow_id=flow.flow_id,
        flow_name=flow.name,
        project_id=flow.scope_id if flow.scope == "project" else None,
        event=event,
        actions=result.get("actions_executed", []),
    )
    logger.info(
        "butler cron gefeuert: %s/%s @%s matched=%s agent_errors=%s",
        flow.owner, flow.flow_id, fired_at.isoformat(), result.get("matched"),
        len(outcome.errors),
    )


async def _run_flow(flow: Flow, event: TriggerEvent, fired_at: datetime) -> None:
    try:
        await asyncio.wait_for(
            _execute_flow(flow, event, fired_at), timeout=_RUN_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.error(
            "butler cron Zeitlimit überschritten; Lauf abgebrochen: %s/%s",
            flow.owner, flow.flow_id,
        )
    except Exception as exc:
        logger.warning(
            "butler cron dispatch fehlgeschlagen %s/%s: %s",
            flow.owner, flow.flow_id, exc,
        )


def _forget_task(key: tuple[str, str], task: asyncio.Task[None]) -> None:
    if _RUNNING.get(key) is task:
        _RUNNING.pop(key, None)
    if not task.cancelled():
        task.exception()


def _start_flow(flow: Flow, event: TriggerEvent, fired_at: datetime) -> None:
    key = (flow.owner, flow.flow_id)
    task = asyncio.create_task(
        _run_flow(flow, event, fired_at),
        name=f"butler-cron-{flow.owner}-{flow.flow_id}",
    )
    _RUNNING[key] = task
    task.add_done_callback(lambda done, task_key=key: _forget_task(task_key, done))


async def _tick(since: datetime, now: datetime) -> int:
    """Plant je fälligem, derzeit nicht laufendem Flow höchstens einen Lauf."""
    fired = 0
    for flow in bp.list_flows(owner=None):
        if not flow.enabled:
            continue
        node = _cron_trigger(flow)
        if node is None:
            continue
        cron_expr = str(node.params.get("cron") or "").strip()
        if not cron_expr:
            continue
        try:
            fire_times = _fire_times(cron_expr, since, now)
        except Exception as exc:
            logger.warning(
                "butler cron: ungültige Expression in Flow %s/%s: %r (%s)",
                flow.owner, flow.flow_id, cron_expr, exc,
            )
            continue
        if not fire_times:
            continue
        key = (flow.owner, flow.flow_id)
        running = _RUNNING.get(key)
        if running is not None and not running.done():
            logger.info(
                "butler cron übersprungen, Flow läuft bereits: %s/%s",
                flow.owner, flow.flow_id,
            )
            continue
        fired_at = fire_times[-1]
        schedule_id = str(node.params.get("schedule_id") or "").strip()
        event = TriggerEvent(
            event_type="cron",
            payload={"schedule_id": schedule_id} if schedule_id else {},
            owner=flow.owner,
            timestamp=fired_at.isoformat(),
        )
        _start_flow(flow, event, fired_at)
        fired += 1
    await asyncio.sleep(0)
    return fired


async def _cancel_running() -> None:
    tasks = list(_RUNNING.values())
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    _RUNNING.clear()


async def run_loop(stop: asyncio.Event) -> None:
    """Prüft die Cron-Flows im Minutentakt und beendet Läufe beim Shutdown."""
    try:
        try:
            await asyncio.wait_for(stop.wait(), timeout=_STARTUP_DELAY)
            return
        except TimeoutError:
            pass
        since = datetime.now(timezone.utc)
        while not stop.is_set():
            now = datetime.now(timezone.utc)
            try:
                await _tick(since, now)
            except Exception as exc:
                logger.warning("butler cron scheduler fehler: %s", exc)
            since = now
            try:
                await asyncio.wait_for(stop.wait(), timeout=_TICK_INTERVAL)
            except TimeoutError:
                pass
    finally:
        await _cancel_running()
