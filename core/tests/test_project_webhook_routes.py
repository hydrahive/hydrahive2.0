"""Projekt-Webhook: Secret einsehen und neu erzeugen.

Bisher wurde das Secret bei jedem Projekt erzeugt und vom Butler-Endpoint
verlangt, war aber nirgends einsehbar. Jetzt liefert GET /webhook URL und
Secret für Projekt-Admins, POST /webhook/rotate erzeugt ein neues und
schreibt einen Audit-Eintrag ohne den Wert.
"""
from __future__ import annotations

from hydrahive.projects import audit, config as project_config


def _create_project(client, admin_headers, members=None) -> str:
    body = {"name": "Webhook-Projekt", "llm_model": "test/model"}
    if members is not None:
        body["members"] = members
    r = client.post("/api/projects", headers=admin_headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_projekt_admin_sieht_url_und_secret(client, admin_headers):
    pid = _create_project(client, admin_headers)
    r = client.get(f"/api/projects/{pid}/webhook", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url_path"] == f"/api/butler/webhooks/project/{pid}"
    assert body["secret"] == project_config.get(pid)["webhook_secret"]
    assert len(body["secret"]) >= 32


def test_mitglied_mit_write_bekommt_403(client, admin_headers, auth_headers):
    pid = _create_project(client, admin_headers,
                          members=[{"username": "testuser", "role": "write"}])
    r = client.get(f"/api/projects/{pid}/webhook", headers=auth_headers)
    assert r.status_code == 403
    assert "secret" not in r.text


def test_fremder_bekommt_403(client, admin_headers, auth_headers):
    pid = _create_project(client, admin_headers)
    r = client.get(f"/api/projects/{pid}/webhook", headers=auth_headers)
    assert r.status_code == 403
    r = client.post(f"/api/projects/{pid}/webhook/rotate", headers=auth_headers)
    assert r.status_code == 403


def test_unbekanntes_projekt_404(client, admin_headers):
    r = client.get("/api/projects/gibt-es-nicht/webhook", headers=admin_headers)
    assert r.status_code == 404


def test_rotation_erzeugt_neues_secret_und_audit(client, admin_headers):
    pid = _create_project(client, admin_headers)
    alt = project_config.get(pid)["webhook_secret"]
    r = client.post(f"/api/projects/{pid}/webhook/rotate", headers=admin_headers)
    assert r.status_code == 200, r.text
    neu = r.json()["secret"]
    assert neu != alt
    assert project_config.get(pid)["webhook_secret"] == neu
    rows = audit.list_for_project(pid, action="webhook_secret_rotated")
    assert len(rows) == 1
    assert rows[0]["user"] == "admin"
    assert neu not in str(rows[0].get("details") or "")
    assert alt not in str(rows[0].get("details") or "")


def test_rotation_erzeugt_secret_bei_altprojekt_ohne(client, admin_headers):
    pid = _create_project(client, admin_headers)
    project_config.update(pid, webhook_secret="")
    r = client.get(f"/api/projects/{pid}/webhook", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["secret"] == ""
    r = client.post(f"/api/projects/{pid}/webhook/rotate", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()["secret"]) >= 32


def test_projektliste_und_detail_enthalten_kein_secret(client, admin_headers):
    pid = _create_project(client, admin_headers)
    secret = project_config.get(pid)["webhook_secret"]
    for path in ("/api/projects", f"/api/projects/{pid}"):
        r = client.get(path, headers=admin_headers)
        assert r.status_code == 200
        assert secret not in r.text


def test_neues_secret_gilt_am_webhook_endpoint(client, admin_headers):
    pid = _create_project(client, admin_headers)
    alt = project_config.get(pid)["webhook_secret"]
    neu = client.post(f"/api/projects/{pid}/webhook/rotate",
                      headers=admin_headers).json()["secret"]
    r = client.post(f"/api/butler/webhooks/project/{pid}", json={"a": 1},
                    headers={"X-Webhook-Secret": alt})
    assert r.status_code == 403
    r = client.post(f"/api/butler/webhooks/project/{pid}", json={"a": 1},
                    headers={"X-Webhook-Secret": neu})
    assert r.status_code == 202
