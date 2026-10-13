"""Lösch-Routen: mode Pflicht, Name bei „unwiderruflich“, nur Admin, 202 + Auftrag (Spec archiv-system.md, Etappe 2)."""
from __future__ import annotations

import uuid

import pytest

from tests._delete_fixtures import make_agent, make_project

pytest_plugins = ["tests._delete_fixtures"]  # Fixture `archive_root`
from tests.conftest import error_code


@pytest.fixture
def queued(monkeypatch):
    """Aufträge nur einreihen, nicht abarbeiten – so bleibt der Zustand prüfbar."""
    from hydrahive.archive import jobs
    monkeypatch.setattr(jobs, "_start_worker", lambda: None)
    jobs.reset_for_tests()
    yield jobs
    jobs.reset_for_tests()


def _targets():
    a = make_agent("API-Agent")
    p = make_project("API-Projekt")
    from hydrahive.api.middleware import users
    name = f"api-opfer-{uuid.uuid4().hex[:6]}"
    users.create(name, "testpass123", role="user")
    return {"agent": (f"/api/agents/{a['id']}", a["name"]),
            "project": (f"/api/projects/{p['id']}", p["name"]),
            "user": (f"/api/users/{name}", name)}


@pytest.mark.parametrize("kind", ["agent", "project", "user"])
def test_mode_is_required(client, admin_headers, queued, kind) -> None:
    url, _ = _targets()[kind]
    r = client.delete(url, headers=admin_headers)
    assert r.status_code == 409 and error_code(r) == "delete_mode_required"


@pytest.mark.parametrize("kind", ["agent", "project", "user"])
def test_permanent_needs_exact_name(client, admin_headers, queued, kind) -> None:
    url, name = _targets()[kind]
    r = client.delete(url, headers=admin_headers, params={"mode": "permanent", "confirm": name.upper() + " "})
    assert r.status_code == 400 and error_code(r) == "delete_confirm_mismatch"
    assert queued.list_jobs()["queued"] == []


@pytest.mark.parametrize("kind", ["agent", "project", "user"])
def test_only_admin(client, auth_headers, queued, kind) -> None:
    url, name = _targets()[kind]
    r = client.delete(url, headers=auth_headers, params={"mode": "permanent", "confirm": name})
    assert r.status_code == 403


@pytest.mark.parametrize("kind,mode", [("agent", "archive"), ("project", "permanent"), ("user", "archive")])
def test_starts_job(client, admin_headers, queued, kind, mode) -> None:
    url, name = _targets()[kind]
    r = client.delete(url, headers=admin_headers, params={"mode": mode, "confirm": name})

    assert r.status_code == 202
    [job] = queued.list_jobs()["queued"]
    assert job["id"] == r.json()["job_id"] and job["kind"] == kind and job["mode"] == mode


def test_same_object_twice_is_rejected(client, admin_headers, queued) -> None:
    url, name = _targets()["agent"]
    first = client.delete(url, headers=admin_headers, params={"mode": "archive"})
    second = client.delete(url, headers=admin_headers, params={"mode": "permanent", "confirm": name})
    assert first.status_code == 202
    assert second.status_code == 409 and error_code(second) == "delete_in_progress"


def test_unknown_object_is_404(client, admin_headers, queued) -> None:
    r = client.delete("/api/agents/gibt-es-nicht", headers=admin_headers, params={"mode": "archive"})
    assert r.status_code == 404 and error_code(r) == "agent_not_found"


def test_cannot_delete_own_account(client, admin_headers, queued) -> None:
    """Fehler 3: Bisher verhinderte das nur die Oberfläche."""
    r = client.delete("/api/users/admin", headers=admin_headers, params={"mode": "permanent", "confirm": "admin"})
    assert r.status_code == 400 and error_code(r) == "cannot_delete_self"


def test_last_admin_is_never_deleted(archive_root) -> None:
    """Fehler 3, auch wenn der Auftrag nicht vom Admin selbst kommt (z. B. aus der Reihe)."""
    from hydrahive.api.middleware import users
    from hydrahive.archive import deletion

    result = deletion.run("user", "admin", "permanent", actor="jemand-anders")

    assert result["state"] == "failed" and result["error"] == "last_admin_cannot_delete"
    assert users.get_by_username("admin") is not None


def test_preview_route(client, admin_headers, auth_headers, archive_root) -> None:
    a = make_agent("Vorschau-Agent")
    url = "/api/admin/archive/delete-preview"

    ok = client.get(url, headers=admin_headers, params={"kind": "agent", "id": a["id"]})
    missing = client.get(url, headers=admin_headers, params={"kind": "agent", "id": "nix"})
    denied = client.get(url, headers=auth_headers, params={"kind": "agent", "id": a["id"]})

    assert ok.status_code == 200 and ok.json()["name"] == "Vorschau-Agent"
    assert ok.json()["archive"]["possible"] is True and ok.json()["archive"]["path"] == str(archive_root)
    assert missing.status_code == 404 and denied.status_code == 403


def test_jobs_route(client, admin_headers, auth_headers, queued) -> None:
    url, _ = _targets()["agent"]
    client.delete(url, headers=admin_headers, params={"mode": "archive"})

    r = client.get("/api/admin/archive/jobs", headers=admin_headers)

    assert r.status_code == 200 and len(r.json()["queued"]) == 1
    assert client.get("/api/admin/archive/jobs", headers=auth_headers).status_code == 403
