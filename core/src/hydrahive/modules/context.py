from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable
from fastapi import APIRouter

if TYPE_CHECKING:
    from hydrahive.butler.registry import ActionSpec, ConditionSpec, TriggerSpec
    from hydrahive.tools.base import Tool

logger = logging.getLogger(__name__)
CATALOG_KINDS = ("task", "idea")


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


@dataclass(frozen=True)
class CatalogSource:
    """Katalog-Quelle eines Moduls (docs/specs/federation-catalog.md §Katalog-Quellen).

    Alle vier Funktionen sind synchron; der Kern ruft sie positionsgebunden in
    genau dieser Reihenfolge der Parameter auf (ab Etappe 3 über einen Thread):
      list_changed(username, after, limit) -> list[dict]
          after = (updated_at, item_id) | None; sortiert nach (updated_at, item_id),
          nur Zeilen mit (updated_at, item_id) > after
      list_versions(username) -> list[tuple[item_id, updated_at, project_id]]
      get_full(username, item_id) -> dict | None   (Metadaten + Volltext)
      query(usernames, project, status, q, limit, offset) -> list[dict]
    `updated_at` bleibt ein undurchsichtiger Wert der Quelle; verglichen wird nur
    innerhalb derselben `kind`.
    """
    kind: str
    list_changed: Callable[..., Any]
    list_versions: Callable[..., Any]
    get_full: Callable[..., Any]
    query: Callable[..., Any]


class ModuleContext:
    """Was ein Modul beim register() registrieren kann."""

    def __init__(self, module_id: str) -> None:
        self.module_id = module_id
        self.routers: list[APIRouter] = []
        self.device_routers: list[tuple[APIRouter, Callable[..., Any]]] = []
        self.tools: list["Tool"] = []
        self.migrations_rel: str | None = None
        self.service_rel: str | None = None
        self.jobs: list[ModuleJob] = []
        self.butler_triggers: list["TriggerSpec"] = []
        self.butler_conditions: list["ConditionSpec"] = []
        self.butler_actions: list["ActionSpec"] = []
        self.catalog_sources: list[CatalogSource] = []

    def register_router(self, router: APIRouter) -> None:
        self.routers.append(router)

    def register_device_router(self, router: APIRouter, *, auth: Callable[..., Any]) -> None:
        """Router für Geräte ohne Nutzer-Login (z. B. Mining-Rigs, Sensoren).

        Wird unter ``/api/module-device/<id>`` eingehängt — getrennt von den
        login-geschützten ``/api/modules/<id>``-Routen. ``auth`` ist eine
        FastAPI-Dependency, die das Gerät prüft und bei Fehlschlag wirft; der
        Kern hängt sie zwingend vor jede Route (Modul kann sie nicht vergessen)
        und setzt zusätzlich ein Rate-Limit pro Client-IP.
        """
        if auth is None or not callable(auth):
            raise ValueError("register_device_router braucht eine auth-Dependency")
        self.device_routers.append((router, auth))

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

    def register_catalog_source(
        self,
        kind: str,
        list_changed: Callable[..., Any],
        list_versions: Callable[..., Any],
        get_full: Callable[..., Any],
        query: Callable[..., Any],
    ) -> None:
        """Modul als Katalog-Quelle für `kind` ("task" | "idea") anmelden.

        Je `kind` höchstens eine Quelle: doppelt im selben Modul → ValueError;
        meldet ein zweites Modul dieselbe `kind` an, übernimmt der Kern beim Start
        nur die erste (modules/catalog_sources.py, Warnung im Log).
        """
        if kind not in CATALOG_KINDS:
            raise ValueError(f"unbekannte Katalog-Art: {kind!r} (erlaubt: {', '.join(CATALOG_KINDS)})")
        fns = {"list_changed": list_changed, "list_versions": list_versions,
               "get_full": get_full, "query": query}
        for name, fn in fns.items():
            if not callable(fn):
                raise ValueError(f"register_catalog_source: {name} muss aufrufbar sein")
        if any(s.kind == kind for s in self.catalog_sources):
            raise ValueError(f"Katalog-Quelle für {kind!r} ist bereits angemeldet")
        self.catalog_sources.append(CatalogSource(kind=kind, **fns))

    def catalog_changed(self, kind: str, username: str, item_id: str) -> None:
        """Nach jedem erfolgreichen Schreiben (anlegen/ändern/löschen) aufrufen.

        Kehrt sofort zurück und wirft nie. Ist der Katalog-Sync aus, kein aktiver
        Hub gesetzt oder der Nutzer nicht ausgewählt, passiert nichts; sonst wird
        der Eintrag für den nächsten Push vorgemerkt (federation/catalog_changes.py).
        """
        try:
            from hydrahive.federation import catalog_changes
            catalog_changes.mark_changed(kind, username, item_id)
        except Exception as e:  # nie in den Schreibpfad des Moduls durchreichen
            logger.debug("catalog_changed(%s) von Modul %s ignoriert: %s", kind, self.module_id, e)
