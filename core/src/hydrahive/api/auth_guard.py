"""Auth-Wächter: findet API-Routen ohne Anmelde-Abhängigkeit (Task 589ff768).

Geht über alle Routen einer FastAPI-App unter ``/api`` (HTTP und WebSocket) und
sucht rekursiv in der Abhängigkeitskette (``route.dependant.dependencies``) nach
einer Auth-Abhängigkeit aus ``api/middleware/auth.py`` bzw. ``access/deps.py``.
Router-Abhängigkeiten (``include_router(..., dependencies=...)``) stehen dort mit
drin, Modul-Routen mit ``require_capability`` zählen also mit.

``get_current_user_optional`` zählt NICHT: Es wirft nie, die Route muss selbst
prüfen. Solche Routen gehören auf die Ausnahmeliste (``api/open_routes.py``).

Wiederverwendbar (z. B. später im Modul-Repo): ``audit(app, exceptions)`` liefert
die Liste der Probleme als Text, leer = alles in Ordnung. Geräte-Router der Module
(``register_device_router``) bringen eine eigene ``auth``-Abhängigkeit mit, die der
Kern zwingend vorschaltet; sie zählt als Auth (``device_auth_calls``).
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute, APIWebSocketRoute

from hydrahive.api.middleware import auth as _auth

WS = "WS"                        # Methode für WebSocket-Routen
MAX_DEPTH = 12                   # Abhängigkeitsketten sind kurz; schützt vor Schleifen

# Abhängigkeiten, die ohne gültige Anmeldung werfen (401/403). Nicht dabei:
# get_current_user_optional (wirft nie) und HTTPBearer (liest nur den Header).
CORE_AUTH_CALLS: frozenset[Callable[..., Any]] = frozenset({
    _auth.require_auth,
    _auth.require_principal,
    _auth.require_principal_or_query,
    _auth.require_session_principal,
    _auth.require_admin,
    _auth.require_admin_principal,
})


@dataclass(frozen=True)
class OpenRoute:
    """Eine Route, die bewusst ohne Auth-Abhängigkeit auskommt, weil sie selbst prüft."""
    method: str                  # GET, POST, … oder WS
    path: str                    # Pfadvorlage wie in der App, z. B. /api/butler/webhooks/project/{project_id}
    reason: str                  # warum offen und womit sie selbst prüft


def _is_capability(call: Callable[..., Any]) -> bool:
    # require_capability(...) liefert eine Closure; sie hängt selbst an require_principal(_or_query),
    # die Rekursion fände das auch. Der Name macht die Meldungen lesbarer.
    return getattr(call, "__qualname__", "").startswith("require_capability.")


def device_auth_calls() -> set[Callable[..., Any]]:
    """auth-Abhängigkeiten der Geräte-Router geladener Module (vom Kern zwingend vorgeschaltet)."""
    from hydrahive.modules.registry import REGISTRY
    calls: set[Callable[..., Any]] = set()
    for entry in REGISTRY.values():
        if entry.loaded and entry.ctx:
            calls.update(auth for _router, auth in entry.ctx.device_routers)
    return calls


def has_auth(dependant: Any, auth_calls: Iterable[Callable[..., Any]], _depth: int = 0) -> bool:
    """True, wenn irgendwo in der Kette eine Auth-Abhängigkeit hängt."""
    if dependant is None or _depth > MAX_DEPTH:
        return False
    known = auth_calls if isinstance(auth_calls, (set, frozenset)) else set(auth_calls)
    for dep in dependant.dependencies:
        if dep.call in known or _is_capability(dep.call):
            return True
        if has_auth(dep, known, _depth + 1):
            return True
    return False


def _methods(route: APIRoute | APIWebSocketRoute) -> list[str]:
    if isinstance(route, APIWebSocketRoute):
        return [WS]
    return sorted(route.methods or [])


def unguarded(app: FastAPI, *, prefix: str = "/api",
              extra_auth: Iterable[Callable[..., Any]] = ()) -> list[tuple[str, str]]:
    """(Methode, Pfad) aller Routen unter ``prefix`` ohne Auth-Abhängigkeit."""
    auth_calls = set(CORE_AUTH_CALLS) | set(extra_auth) | device_auth_calls()
    out: list[tuple[str, str]] = []
    for route in app.routes:
        if not isinstance(route, (APIRoute, APIWebSocketRoute)) or not route.path.startswith(prefix):
            continue
        if not has_auth(route.dependant, auth_calls):
            out += [(method, route.path) for method in _methods(route)]
    return sorted(set(out), key=lambda mp: (mp[1], mp[0]))


def all_routes(app: FastAPI, *, prefix: str = "/api") -> set[tuple[str, str]]:
    """(Methode, Pfad) aller Routen unter ``prefix``, für die Prüfung auf veraltete Einträge."""
    return {(method, route.path) for route in app.routes
            if isinstance(route, (APIRoute, APIWebSocketRoute)) and route.path.startswith(prefix)
            for method in _methods(route)}


def audit(app: FastAPI, exceptions: Iterable[OpenRoute], *, prefix: str = "/api",
          extra_auth: Iterable[Callable[..., Any]] = ()) -> list[str]:
    """Probleme als lesbarer Text, leer = in Ordnung.

    - Route ohne Auth, nicht auf der Liste → ``ohne Auth: GET /api/x``
    - Listeneintrag ohne Begründung → ``ohne Begründung: …``
    - Listeneintrag ohne passende Route → ``veraltet: …``
    - Listeneintrag doppelt → ``doppelt: …``
    - Listeneintrag für eine Route, die inzwischen Auth hat → ``unnötig: …``
    """
    entries = list(exceptions)
    problems: list[str] = []
    listed: set[tuple[str, str]] = set()
    for e in entries:
        key = (e.method, e.path)
        if key in listed:
            problems.append(f"doppelt: {e.method} {e.path}")
        listed.add(key)
        if not (e.reason or "").strip():
            problems.append(f"ohne Begründung: {e.method} {e.path}")
    existing = all_routes(app, prefix=prefix)
    open_now = set(unguarded(app, prefix=prefix, extra_auth=extra_auth))
    problems += [f"ohne Auth: {m} {p}" for m, p in sorted(open_now - listed, key=lambda mp: (mp[1], mp[0]))]
    for m, p in sorted(listed, key=lambda mp: (mp[1], mp[0])):
        if (m, p) not in existing:
            problems.append(f"veraltet: {m} {p} (Route gibt es nicht mehr)")
        elif (m, p) not in open_now:
            problems.append(f"unnötig: {m} {p} (Route hat inzwischen eine Auth-Abhängigkeit)")
    return problems
