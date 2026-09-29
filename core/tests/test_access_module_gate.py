"""Modul-Router-Gate (Plan P3, Task 3.2).

mount_module_routers hängt an jeden Modul-Router require_capability("module.<id>").
Module ohne Angaben im Manifest bleiben für alle offen.
"""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hydrahive.access import capabilities, grants


def _write_module(root, mid: str, caps=None) -> None:
    md = root / "modules" / mid
    (md / "backend").mkdir(parents=True)
    manifest = {"id": mid, "name": mid, "version": "1.0.0"}
    if caps is not None:
        manifest["capabilities"] = caps
    (md / "manifest.json").write_text(json.dumps(manifest))
    (md / "backend" / "__init__.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        "@router.get('/ping')\n"
        "def ping():\n"
        "    return {'ok': True}\n"
        "def register(ctx):\n"
        "    ctx.register_router(router)\n"
    )


@pytest.fixture
def gated_app(mod_env, monkeypatch):
    monkeypatch.setattr(capabilities, "CATALOG", capabilities.Catalog.with_core())
    _write_module(mod_env, "offen")
    _write_module(mod_env, "zu", [{"id": "module.zu", "label": "Zu", "default": "admin_only"}])
    from hydrahive.api import main
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY
    load_all()
    app = FastAPI()
    main.register_module_capabilities()
    main.mount_module_routers(app)
    yield app
    REGISTRY.clear()


def _headers(client, name: str) -> dict:
    r = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_undeclared_module_open(client, gated_app):
    r = TestClient(gated_app).get("/api/modules/offen/ping", headers=_headers(client, "testuser"))
    assert r.status_code == 200


def test_declared_module_denied_without_grant(client, gated_app):
    r = TestClient(gated_app).get("/api/modules/zu/ping", headers=_headers(client, "testuser"))
    assert r.status_code == 403
    assert r.json()["detail"]["params"]["capability"] == "module.zu"


def test_declared_module_admin_allowed(client, gated_app):
    r = TestClient(gated_app).get("/api/modules/zu/ping", headers=_headers(client, "admin"))
    assert r.status_code == 200


def test_declared_module_allowed_with_grant(client, gated_app):
    grants.grant("module.zu", "everyone", "", "use", actor_id="adm")
    r = TestClient(gated_app).get("/api/modules/zu/ping", headers=_headers(client, "testuser"))
    assert r.status_code == 200


def test_catalog_filled_from_manifests(client, gated_app):
    cat = capabilities.catalog()
    assert cat.is_declared("module.zu") and not cat.is_declared("module.offen")
