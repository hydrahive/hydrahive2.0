"""Durchsetzung an Schnittstellen (Plan P3, Tasks 3.1–3.3).

require_capability als Dependency, Gate für Modul-Router und für die Core-Router
von VMs, Containern und Föderation. Solange eine Funktion nicht deklariert ist,
bleibt alles wie bisher.
"""
from __future__ import annotations

import json

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from hydrahive.access import capabilities, grants
from hydrahive.access.deps import require_capability
from hydrahive.modules.manifest import ModuleManifest


def _uid(client, admin_headers, name: str = "testuser") -> str:
    users = client.get("/api/users", headers=admin_headers).json()
    return next(u["user_id"] for u in users if u["username"] == name)


@pytest.fixture
def fresh_catalog(monkeypatch):
    cat = capabilities.Catalog.with_core()
    monkeypatch.setattr(capabilities, "CATALOG", cat)
    return cat


def _register(cat, tmp_path, mid: str, caps) -> None:
    p = tmp_path / f"{mid}.json"
    p.write_text(json.dumps({"id": mid, "name": mid, "version": "1.0.0", "capabilities": caps}))
    cat.register_module(ModuleManifest.load(p))


# ── Task 3.1: Dependency ──────────────────────────────────────────────────

def _mini_app(cap: str) -> FastAPI:
    app = FastAPI()
    r = APIRouter()

    @r.get("/x", dependencies=[Depends(require_capability(cap))])
    def x() -> dict:
        return {"ok": True}

    app.include_router(r)
    return app


def test_dependency_denies_without_grant(client, auth_headers, fresh_catalog, tmp_path):
    _register(fresh_catalog, tmp_path, "gt", [{"id": "module.gt", "label": "x", "default": "admin_only"}])
    r = TestClient(_mini_app("module.gt")).get("/x", headers=auth_headers)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "capability_denied"
    assert r.json()["detail"]["params"]["capability"] == "module.gt"


def test_dependency_allows_admin(client, admin_headers, fresh_catalog, tmp_path):
    _register(fresh_catalog, tmp_path, "gt", [{"id": "module.gt", "label": "x", "default": "admin_only"}])
    assert TestClient(_mini_app("module.gt")).get("/x", headers=admin_headers).status_code == 200


def test_dependency_allows_granted_user(client, auth_headers, admin_headers, fresh_catalog, tmp_path):
    _register(fresh_catalog, tmp_path, "gt", [{"id": "module.gt", "label": "x", "default": "admin_only"}])
    grants.grant("module.gt", "user", _uid(client, admin_headers), "use", actor_id="adm")
    assert TestClient(_mini_app("module.gt")).get("/x", headers=auth_headers).status_code == 200


def test_dependency_open_for_undeclared(client, auth_headers, fresh_catalog):
    assert TestClient(_mini_app("module.gibtsnicht")).get("/x", headers=auth_headers).status_code == 200


def test_dependency_requires_login(client, fresh_catalog):
    assert TestClient(_mini_app("module.gibtsnicht")).get("/x").status_code == 401


# ── Task 3.3: Core-Router ─────────────────────────────────────────────────

_CORE = [
    ("core.vms", "get", "/api/vms"),
    ("core.containers", "get", "/api/containers"),
    ("core.federation", "get", "/api/federation/workstations"),
]


@pytest.mark.parametrize("cap,method,path", _CORE)
def test_core_router_denied_without_grant(client, auth_headers, fresh_catalog, cap, method, path):
    r = client.request(method.upper(), path, headers=auth_headers)
    assert r.status_code == 403, (path, r.status_code, r.text[:200])
    assert r.json()["detail"]["params"]["capability"] == cap


@pytest.mark.parametrize("cap,method,path", _CORE)
def test_core_router_allowed_with_grant(client, auth_headers, admin_headers, fresh_catalog, cap, method, path):
    grants.grant(cap, "user", _uid(client, admin_headers), "use", actor_id="adm")
    r = client.request(method.upper(), path, headers=auth_headers)
    assert r.status_code != 403, (path, r.status_code, r.text[:200])


@pytest.mark.parametrize("cap,method,path", _CORE)
def test_core_router_admin_unaffected(client, admin_headers, fresh_catalog, cap, method, path):
    assert client.request(method.upper(), path, headers=admin_headers).status_code != 403


def test_core_router_open_when_capability_not_declared(client, auth_headers, monkeypatch):
    empty = capabilities.Catalog()
    monkeypatch.setattr(capabilities, "CATALOG", empty)
    assert client.get("/api/vms", headers=auth_headers).status_code != 403
