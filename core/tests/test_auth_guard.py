"""Auth-Wächter (Task 589ff768, Abnahme W1/W2).

W1: Jede API-Route der echten App hat eine Auth-Abhängigkeit oder steht mit Begründung
auf der Ausnahmeliste (``api/open_routes.py``). Neue Route ohne Auth → rot mit Methode
und Pfad in der Meldung.
W2: Einträge ohne Begründung, veraltete (Route weg), doppelte und unnötige Einträge → rot.

Die Gegenproben laufen gegen eine kleine Test-App und gegen eine Kopie der echten
Routen mit einer zusätzlichen offenen Route; die echte App wird nicht verändert.
"""
from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, FastAPI, WebSocket

from hydrahive.access.deps import require_capability
from hydrahive.api.auth_guard import WS, OpenRoute, audit, has_auth, unguarded
from hydrahive.api.middleware.auth import get_current_user_optional, require_admin, require_auth
from hydrahive.api.open_routes import OPEN_ROUTES


def _real_app():
    from hydrahive.api import main
    return main.app


def test_echte_app_alle_routen_mit_auth_oder_begruendeter_ausnahme(client):
    problems = audit(_real_app(), OPEN_ROUTES)
    assert problems == [], "Auth-Wächter:\n  " + "\n  ".join(problems) + (
        "\nNeue Route ohne Auth? Auth-Abhängigkeit ergänzen (require_auth/require_principal/…) "
        "oder mit Begründung und Test in api/open_routes.py eintragen.")


def test_echte_app_viele_routen_geprueft(client):
    from hydrahive.api.auth_guard import all_routes
    routes = all_routes(_real_app())
    assert len(routes) > 400                                  # Stand 23.11.: 542 HTTP + 2 WebSocket
    assert len(unguarded(_real_app())) == len(OPEN_ROUTES)


def test_jede_ausnahme_hat_begruendung_und_ist_eindeutig():
    keys = [(e.method, e.path) for e in OPEN_ROUTES]
    assert len(keys) == len(set(keys))
    assert all(len(e.reason.strip()) >= 30 for e in OPEN_ROUTES)


# --- Gegenproben an einer kleinen App ----------------------------------------------

def _mini_app() -> FastAPI:
    app = FastAPI()
    guarded = APIRouter(prefix="/api/guarded", dependencies=[Depends(require_auth)])

    @guarded.get("/x")
    def x():
        return {}

    @app.get("/api/admin")
    def admin(_: Annotated[tuple[str, str], Depends(require_admin)]):
        return {}

    @app.get("/api/cap", dependencies=[Depends(require_capability("core.vms"))])
    def cap():
        return {}

    @app.get("/api/open")
    def open_route():
        return {}

    @app.get("/api/optional")
    def optional(_: Annotated[object, Depends(get_current_user_optional)]):
        return {}

    @app.websocket("/api/ws")
    async def ws(socket: WebSocket):
        await socket.close()

    @app.get("/not-api")
    def not_api():
        return {}

    app.include_router(guarded)
    return app


def test_router_admin_und_capability_zaehlen_als_auth():
    assert unguarded(_mini_app()) == [("GET", "/api/open"), ("GET", "/api/optional"), (WS, "/api/ws")]


def test_neue_route_ohne_auth_wird_mit_methode_und_pfad_gemeldet():
    problems = audit(_mini_app(), [OpenRoute("GET", "/api/optional", "prüft selbst ?token= für <img>-Links"),
                                   OpenRoute(WS, "/api/ws", "prüft ?token= selbst, Browser senden keinen Header")])
    assert problems == ["ohne Auth: GET /api/open"]


def test_websocket_ohne_auth_wird_gemeldet():
    problems = audit(_mini_app(), [OpenRoute("GET", "/api/open", "Testroute ohne Daten, nur für den Test"),
                                   OpenRoute("GET", "/api/optional", "prüft selbst ?token= für <img>-Links")])
    assert problems == ["ohne Auth: WS /api/ws"]


def test_get_current_user_optional_zaehlt_nicht_als_auth():
    route = next(r for r in _mini_app().routes if getattr(r, "path", "") == "/api/optional")
    assert has_auth(route.dependant, {require_auth}) is False


@pytest.mark.parametrize("entry,expected", [
    (OpenRoute("GET", "/api/open", ""), "ohne Begründung: GET /api/open"),
    (OpenRoute("GET", "/api/open", "   "), "ohne Begründung: GET /api/open"),
    (OpenRoute("GET", "/api/gibt-es-nicht", "früher offen, inzwischen entfernt"),
     "veraltet: GET /api/gibt-es-nicht (Route gibt es nicht mehr)"),
    (OpenRoute("POST", "/api/open", "falsche Methode, die Route kennt nur GET"),
     "veraltet: POST /api/open (Route gibt es nicht mehr)"),
    (OpenRoute("GET", "/api/admin", "hat längst require_admin, Eintrag überflüssig"),
     "unnötig: GET /api/admin (Route hat inzwischen eine Auth-Abhängigkeit)"),
])
def test_fehlerhafte_listeneintraege_werden_rot(entry, expected):
    base = [OpenRoute("GET", "/api/open", "Testroute ohne Daten, nur für den Test"),
            OpenRoute("GET", "/api/optional", "prüft selbst ?token= für <img>-Links"),
            OpenRoute(WS, "/api/ws", "prüft ?token= selbst, Browser senden keinen Header")]
    entries = [e for e in base if (e.method, e.path) != (entry.method, entry.path)] + [entry]
    assert expected in audit(_mini_app(), entries)


def test_doppelter_eintrag_wird_rot():
    entry = OpenRoute("GET", "/api/open", "Testroute ohne Daten, nur für den Test")
    problems = audit(_mini_app(), [entry, entry, OpenRoute("GET", "/api/optional", "prüft selbst ?token="),
                                   OpenRoute(WS, "/api/ws", "prüft ?token= selbst")])
    assert problems == ["doppelt: GET /api/open"]


def test_gegenprobe_echte_routen_plus_offene_testroute(client):
    """Kopie der echten Routen + eine offene Testroute: rot mit Methode und Pfad (Beleg für W1)."""
    copy = FastAPI()
    copy.router.routes.extend(_real_app().routes)

    @copy.delete("/api/neu/ohne-auth/{item_id}")
    def neu(item_id: str):
        return {}

    assert audit(copy, OPEN_ROUTES) == ["ohne Auth: DELETE /api/neu/ohne-auth/{item_id}"]
    assert audit(_real_app(), OPEN_ROUTES) == []              # echte App unverändert


def test_nachgebaute_capability_closure_zaehlt_nicht():
    """Nur die echte require_capability-Closure aus access/deps zählt, kein gleichnamiger Nachbau."""
    def _dep():
        return None
    _dep.__qualname__ = "require_capability.<locals>._dep"
    app = FastAPI()

    @app.get("/api/nachbau", dependencies=[Depends(_dep)])
    def nachbau():
        return {}

    assert unguarded(app) == [("GET", "/api/nachbau")]


def test_praefix_trifft_nur_ganze_pfadteile():
    app = FastAPI()

    @app.get("/apix/offen")
    def apix():
        return {}

    @app.get("/api")
    def api_root():
        return {}

    assert unguarded(app) == [("GET", "/api")]
