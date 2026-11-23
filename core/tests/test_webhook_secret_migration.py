"""Start-Migration: Projekte ohne Webhook-Secret bekommen eines (Task 44fffa23, B1/B2)."""
from __future__ import annotations

import uuid

from hydrahive.projects import audit, config as project_config
from hydrahive.projects._webhook_migration import ensure_webhook_secrets
from tests._delete_fixtures import make_project


def _altprojekt(**extra) -> str:
    p = make_project(f"Altprojekt {uuid.uuid4().hex[:6]}", created_by=extra.pop("owner", "testuser"))
    project_config.update(p["id"], webhook_secret="", **extra)
    return p["id"]


def test_migration_erzeugt_secret_idempotent_mit_audit():
    pid = _altprojekt()
    ensure_webhook_secrets()
    cfg = project_config.get(pid)
    secret = cfg["webhook_secret"]
    assert len(secret) >= 32 and cfg["webhook_secret_auto"] is True
    rows = audit.list_for_project(pid, action="webhook_secret_generated")
    assert len(rows) == 1 and secret not in str(rows[0])

    assert ensure_webhook_secrets() == 0                       # zweiter Lauf: nichts
    assert project_config.get(pid)["webhook_secret"] == secret
    assert len(audit.list_for_project(pid, action="webhook_secret_generated")) == 1


def test_migration_fasst_vorhandenes_secret_nicht_an():
    p = make_project(f"Mit-Secret {uuid.uuid4().hex[:6]}")
    alt = project_config.get(p["id"])["webhook_secret"]
    ensure_webhook_secrets()
    cfg = project_config.get(p["id"])
    assert cfg["webhook_secret"] == alt and not cfg.get("webhook_secret_auto")
    assert audit.list_for_project(p["id"], action="webhook_secret_generated") == []


def test_migration_behandelt_leerzeichen_secret_als_fehlend():
    pid = _altprojekt()
    project_config.update(pid, webhook_secret="   ")
    ensure_webhook_secrets()
    assert project_config.get(pid)["webhook_secret"].strip()


def test_webhook_401_403_202(client):
    pid = _altprojekt()
    url = f"/api/butler/webhooks/project/{pid}"
    # vor der Migration: abgelehnt
    assert client.post(url, json={}).status_code == 401
    ensure_webhook_secrets()
    secret = project_config.get(pid)["webhook_secret"]
    assert client.post(url, json={}).status_code == 401
    assert client.post(url, json={}, headers={"X-Webhook-Secret": "falsch"}).status_code == 403
    assert client.post(url, json={}, headers={"X-Webhook-Secret": secret}).status_code == 202


def test_hinweis_flag_in_route_ack_und_rotation(client, admin_headers):
    pid = _altprojekt()
    ensure_webhook_secrets()
    r = client.get(f"/api/projects/{pid}/webhook", headers=admin_headers)
    assert r.json()["auto_generated"] is True
    assert client.get(f"/api/projects/{pid}", headers=admin_headers).json()["webhook_secret_auto"] is True
    secret = r.json()["secret"]
    assert client.post(f"/api/projects/{pid}/webhook/ack", headers=admin_headers).status_code == 204
    r = client.get(f"/api/projects/{pid}/webhook", headers=admin_headers)
    assert r.json()["auto_generated"] is False and r.json()["secret"] == secret

    pid2 = _altprojekt()
    ensure_webhook_secrets()
    r = client.post(f"/api/projects/{pid2}/webhook/rotate", headers=admin_headers)
    assert r.json()["auto_generated"] is False
    assert project_config.get(pid2)["webhook_secret_auto"] is False


def test_ack_nur_fuer_projekt_admin(client, admin_headers, auth_headers):
    pid = _altprojekt(owner="admin")                            # testuser ist kein Mitglied
    ensure_webhook_secrets()
    assert client.post(f"/api/projects/{pid}/webhook/ack", headers=auth_headers).status_code == 403
    assert project_config.get(pid)["webhook_secret_auto"] is True
    assert client.post(f"/api/projects/{pid}/webhook/ack").status_code in (401, 403)
