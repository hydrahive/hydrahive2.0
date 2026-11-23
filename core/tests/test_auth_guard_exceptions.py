"""Auth-Wächter W3 (Task 589ff768): Jede Ausnahme aus ``api/open_routes.py`` (außer Login
und Health) gibt ohne gültige Anmeldung bzw. Signatur nichts preis.

Je Ausnahme mindestens ein Fall ohne Nachweis und einer mit gefälschtem Nachweis. Geprüft
wird der Statuscode und, dass in der Antwort nur ein Fehlercode steht (keine Nutzdaten).
``test_jede_ausnahme_hat_einen_fall`` sorgt dafür, dass eine neue Ausnahme ohne Test rot wird.
"""
from __future__ import annotations

import uuid

import pytest
from starlette.websockets import WebSocketDisconnect

from hydrahive.api.auth_guard import WS
from hydrahive.api.open_routes import OPEN_ROUTES

EXEMPT = {("POST", "/api/auth/login"), ("GET", "/api/health")}
FAKE_JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiJ9.gefaelscht"
PEER_HEADERS = {"X-HH-Peer": "ZZZZ" * 16, "X-HH-Signature": "AAAA"}

# (Methode, Pfadvorlage) → Liste von (URL, Anfrage-Argumente, erlaubte Statuscodes)
HTTP_CASES: dict[tuple[str, str], list[tuple[str, dict, set[int]]]] = {
    ("GET", "/api/files"): [
        ("/api/files?path=/etc/passwd", {}, {401}),
        (f"/api/files?path=/etc/passwd&token={FAKE_JWT}", {}, {401}),
        ("/api/files?path=/etc/passwd", {"headers": {"Authorization": f"Bearer {FAKE_JWT}"}}, {401}),
    ],
    ("GET", "/api/agentlink/dashboard-auth"): [
        ("/api/agentlink/dashboard-auth", {}, {401}),
        ("/api/agentlink/dashboard-auth", {"cookies": {"hh_agentlink": "gefaelscht.wert"}}, {401}),
    ],
    ("POST", "/api/communication/whatsapp/incoming"): [
        ("/api/communication/whatsapp/incoming",
         {"json": {"target_username": "admin", "external_user_id": "x", "text": "hi"}}, {401}),
        ("/api/communication/whatsapp/incoming",
         {"json": {"target_username": "admin", "external_user_id": "x", "text": "hi"},
          "headers": {"X-HH-Bridge-Secret": "falsch"}}, {401}),
    ],
    ("POST", "/api/compute/agent/enroll"): [
        ("/api/compute/agent/enroll", {"content": b"{}"}, {400}),
        ("/api/compute/agent/enroll",
         {"content": b'{"token":"' + b"a" * 40 + b'","csr_pem":"x","agent_version":"1"}'}, {400, 401, 403, 404}),
    ],
    ("POST", "/api/butler/webhooks/project/{project_id}"): [
        ("/api/butler/webhooks/project/gibt-es-nicht", {"json": {}}, {404}),
    ],
    **{("POST", f"/api/peering/{p}"): [
        (f"/api/peering/{p}", {"json": {"kind": "x"}}, {403, 404}),
        (f"/api/peering/{p}", {"json": {"kind": "x"}, "headers": PEER_HEADERS}, {403, 404}),
    ] for p in ("tasks", "replies", "catalog/push", "catalog/pull", "catalog/notify", "catalog/read", "catalog/fetch")},
}

WS_CASES: dict[tuple[str, str], list[tuple[str, dict, set[int]]]] = {
    (WS, "/api/containers/{container_id}/console"): [
        ("/api/containers/x/console", {}, {4401}),
        (f"/api/containers/x/console?token={FAKE_JWT}", {}, {4401}),
    ],
    (WS, "/api/compute/agent/connect"): [
        ("/api/compute/agent/connect", {}, {4403}),
        ("/api/compute/agent/connect", {"headers": {"x-hydrahive-node-id": "n1", "x-hydrahive-client-cert": "x",
                                                    "x-hydrahive-proxy-secret": "falsch"}}, {4403}),
    ],
}


def _only_error(body) -> bool:
    """Antwort enthält nur einen Fehlercode, keine Nutzdaten."""
    if body in ({}, None, ""):
        return True
    if isinstance(body, dict) and set(body) == {"detail"}:
        d = body["detail"]
        return isinstance(d, str) or (isinstance(d, dict) and set(d) <= {"code", "message", "retry_after"})
    return False


def test_jede_ausnahme_hat_einen_fall():
    listed = {(e.method, e.path) for e in OPEN_ROUTES} - EXEMPT
    covered = set(HTTP_CASES) | set(WS_CASES)
    assert listed - covered == set(), f"Ausnahme ohne W3-Test: {sorted(listed - covered)}"
    assert covered - listed == set(), f"Test für Route, die nicht (mehr) auf der Liste steht: {sorted(covered - listed)}"


@pytest.mark.parametrize("key,url,kwargs,allowed", [
    (k, u, kw, ok) for k, cases in HTTP_CASES.items() for u, kw, ok in cases
], ids=lambda v: v if isinstance(v, str) else None)
def test_ohne_gueltigen_nachweis_keine_daten(client, key, url, kwargs, allowed):
    r = client.request(key[0], url, **kwargs)
    assert r.status_code in allowed, f"{key[0]} {url}: {r.status_code} {r.text[:200]}"
    assert _only_error(r.json() if r.content else None), f"{key[0]} {url} gibt Daten preis: {r.text[:200]}"


@pytest.mark.parametrize("key,url,kwargs,codes", [
    (k, u, kw, ok) for k, cases in WS_CASES.items() for u, kw, ok in cases
], ids=lambda v: v if isinstance(v, str) else None)
def test_websocket_ohne_gueltigen_nachweis_geschlossen(client, key, url, kwargs, codes):
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(url, **kwargs) as ws:
            ws.receive_text()                                 # darf nie Daten liefern
    assert closed.value.code in codes


def test_butler_webhook_mit_falschem_secret(client):
    """Projekt mit Secret: ohne bzw. mit falschem X-Webhook-Secret 401/403, kein Flow."""
    from tests._delete_fixtures import make_project
    p = make_project(f"Webhook-Waechter {uuid.uuid4().hex[:6]}")
    url = f"/api/butler/webhooks/project/{p['id']}"
    r = client.post(url, json={})
    assert r.status_code == 401 and _only_error(r.json())
    r = client.post(url, json={}, headers={"X-Webhook-Secret": "falsch"})
    assert r.status_code == 403 and _only_error(r.json())


@pytest.mark.xfail(strict=True, reason="Butler-Webhook nimmt Projekte ohne Secret ungeprüft an (Task 1809eae3)")
def test_butler_webhook_projekt_ohne_secret(client):
    """Bewacht die bekannte Lücke: schließt Task 1809eae3 sie, wird dieser Test grün → xfail
    strict meldet das, dann das xfail entfernen."""
    from hydrahive.projects import config as project_config
    from tests._delete_fixtures import make_project
    p = make_project(f"Webhook-ohne-Secret {uuid.uuid4().hex[:6]}")
    project_config.update(p["id"], webhook_secret="")
    r = client.post(f"/api/butler/webhooks/project/{p['id']}", json={})
    assert r.status_code == 401
