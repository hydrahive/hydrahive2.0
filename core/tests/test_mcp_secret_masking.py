"""MCP-Server: env/headers-Werte (oft API-Schlüssel) nur für Admins im Klartext.

Befund 12.10.2026 (Review-Folge): GET /api/mcp/servers und /servers/{id} lieferten allen eingeloggten
Nutzern die vollständige Konfiguration inkl. env/headers. Ändern dürfen ohnehin nur Admins, also braucht
ein normaler Nutzer nur die Schlüsselnamen, nicht die Werte.
"""
from __future__ import annotations

import pytest

GEHEIM = "sk-mcp-geheim-123456"


@pytest.fixture
def servers(client, admin_headers):
    """Ein http-Server (headers) und ein stdio-Server (env) – je nach Transport speichert die Config nur eins."""
    bodies = [
        {"id": "mask-http", "name": "Mask HTTP", "transport": "http", "url": "https://example.org/mcp",
         "headers": {"Authorization": f"Bearer {GEHEIM}"}, "enabled": False},
        {"id": "mask-stdio", "name": "Mask STDIO", "transport": "stdio", "command": "true",
         "env": {"API_KEY": GEHEIM}, "enabled": False},
    ]
    for b in bodies:
        r = client.post("/api/mcp/servers", json=b, headers=admin_headers)
        assert r.status_code == 201, r.text
    yield
    for b in bodies:
        client.delete(f"/api/mcp/servers/{b['id']}", headers=admin_headers)


def test_nutzer_sieht_keine_werte_in_der_liste(client, auth_headers, servers):
    r = client.get("/api/mcp/servers", headers=auth_headers)
    assert r.status_code == 200 and GEHEIM not in r.text
    by_id = {x["id"]: x for x in r.json()}
    assert by_id["mask-http"]["headers"] == {"Authorization": "***"}
    assert by_id["mask-stdio"]["env"] == {"API_KEY": "***"}


def test_nutzer_sieht_keine_werte_im_detail(client, auth_headers, servers):
    for sid, field, key in (("mask-http", "headers", "Authorization"), ("mask-stdio", "env", "API_KEY")):
        r = client.get(f"/api/mcp/servers/{sid}", headers=auth_headers)
        assert r.status_code == 200 and GEHEIM not in r.text
        assert r.json()[field] == {key: "***"}


def test_admin_sieht_werte_zum_bearbeiten(client, admin_headers, servers):
    assert client.get("/api/mcp/servers/mask-http", headers=admin_headers).json()["headers"] == {
        "Authorization": f"Bearer {GEHEIM}"}
    assert client.get("/api/mcp/servers/mask-stdio", headers=admin_headers).json()["env"] == {"API_KEY": GEHEIM}


def test_nutzer_ohne_env_bleibt_unveraendert(client, auth_headers, admin_headers):
    body = {"id": "mask-leer", "name": "Leer", "transport": "http", "url": "https://example.org/x", "enabled": False}
    assert client.post("/api/mcp/servers", json=body, headers=admin_headers).status_code == 201
    try:
        s = client.get("/api/mcp/servers/mask-leer", headers=auth_headers).json()
        assert s.get("env") in (None, {}) and s.get("headers") in (None, {})
    finally:
        client.delete("/api/mcp/servers/mask-leer", headers=admin_headers)


def test_for_viewer_veraendert_das_original_nicht():
    """Die Maske darf nur die Antwort betreffen, nie die geladene Konfiguration (sonst landet *** beim Speichern)."""
    from hydrahive.api.routes._mcp_schemas import for_viewer
    cfg = {"id": "x", "env": {"API_KEY": GEHEIM}, "headers": {"Authorization": GEHEIM}}
    assert for_viewer(cfg, "user")["env"] == {"API_KEY": "***"}
    assert cfg["env"] == {"API_KEY": GEHEIM} and cfg["headers"] == {"Authorization": GEHEIM}
