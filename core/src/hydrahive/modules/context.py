from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Awaitable, Callable
from fastapi import APIRouter

if TYPE_CHECKING:
    from hydrahive.butler.registry import ActionSpec, ConditionSpec, TriggerSpec
    from hydrahive.tools.base import Tool


@dataclass(frozen=True)
class ModuleJob:
    """Ein periodischer Hintergrundjob eines Moduls.

    `fn` ist eine async-Funktion ohne Argumente, die das Framework alle
    `interval_seconds` aufruft (mit `initial_delay_seconds` Verzögerung nach
    Start). Muss nicht-blockierend sein (async I/O), sonst blockiert sie den
    Event-Loop. Exceptions werden vom Supervisor isoliert und geloggt — ein
    kaputter Job bricht weder andere Jobs noch den Core.
    """
    name: str
    fn: Callable[[], Awaitable[None]]
    interval_seconds: float
    initial_delay_seconds: float = 5.0


class ModuleContext:
    """Was ein Modul beim register() registrieren kann."""

    def __init__(self, module_id: str) -> None:
        self.module_id = module_id
        self.routers: list[APIRouter] = []
        self.tools: list["Tool"] = []
        self.migrations_rel: str | None = None
        self.service_rel: str | None = None
        self.jobs: list[ModuleJob] = []
        self.butler_triggers: list["TriggerSpec"] = []
        self.butler_conditions: list["ConditionSpec"] = []
        self.butler_actions: list["ActionSpec"] = []

    def register_router(self, router: APIRouter) -> None:
        self.routers.append(router)

    def register_tool(self, tool: "Tool") -> None:
        self.tools.append(tool)

    def register_migrations(self, rel_dir: str) -> None:
        self.migrations_rel = rel_dir

    def register_service(self, rel_dir: str) -> None:
        self.service_rel = rel_dir

    def register_job(
        self,
        name: str,
        fn: Callable[[], Awaitable[None]],
        interval_seconds: float,
        *,
        initial_delay_seconds: float = 5.0,
    ) -> None:
        """Periodischen Hintergrundjob registrieren (Heartbeat/Poller).

        Das Framework startet den Job beim Backend-Start als überwachten Task
        und stoppt ihn beim Shutdown.
        """
        if interval_seconds <= 0:
            raise ValueError("interval_seconds muss > 0 sein")
        if initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds muss >= 0 sein")
        self.jobs.append(ModuleJob(
            name=name,
            fn=fn,
            interval_seconds=interval_seconds,
            initial_delay_seconds=initial_delay_seconds,
        ))

    def register_butler_trigger(self, spec: "TriggerSpec") -> None:
        """Eigenen Butler-Trigger-Subtype beisteuern (z.B. crypto_threshold)."""
        self.butler_triggers.append(spec)

    def register_butler_condition(self, spec: "ConditionSpec") -> None:
        """Eigene Butler-Condition beisteuern."""
        self.butler_conditions.append(spec)

    def register_butler_action(self, spec: "ActionSpec") -> None:
        """Eigene Butler-Action beisteuern."""
        self.butler_actions.append(spec)
