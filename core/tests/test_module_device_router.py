"""Geräte-Router für Module (docs/specs/mining-modul.md §E0).

Module können Endpunkte für Geräte ohne Nutzer-Login anbieten (z. B. Mining-Rigs).
Der Kern erzwingt dabei die vom Modul übergebene Prüfung und ein Rate-Limit;
normale Modul-Router bleiben unverändert hinter dem Login.
"""
from __future__ import annotations

import json

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

_BACKEND = (
    "from fastapi import APIRouter, Header, HTTPException\n"
    "router = APIRouter()\n"
    "@router.get('/ping')\n"
    "def ping():\n"
    "    return {'ok': True}\n"
    "dev = APIRouter()\n"
    "def check(x_device_token: str | None = Header(None)):\n"
    "    if x_device_token != 'good':\n"
    "        raise HTTPException(401, 'bad_token')\n"
    "    return 'rig-1'\n"
    "@dev.post('/report')\n"
    "def report():\n"
    "    return {'stored': True}\n"
    "def register(ctx):\n"
    "    ctx.register_router(router)\n"
    "    ctx.register_device_router(dev, auth=check)\n"
)


@pytest.fixture
def dev_app(mod_env):
    md = mod_env / "modules" / "rigs"
    (md / "backend").mkdir(parents=True)
    (md / "manifest.json").write_text(json.dumps({"id": "rigs", "name": "Rigs", "version": "1.0.0"}))
    (md / "backend" / "__init__.py").write_text(_BACKEND)
    from hydrahive.api import main
    from hydrahive.api.middleware import inbound_ratelimit
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY
    inbound_ratelimit.reset()
    load_all()
    assert REGISTRY["rigs"].loaded, REGISTRY["rigs"].error
    app = FastAPI()
    main.register_module_capabilities()
    main.mount_module_routers(app)
    yield app
    REGISTRY.clear()
    inbound_ratelimit.reset()


def test_register_requires_auth():
    from hydrahive.modules.context import ModuleContext
    ctx = ModuleContext("x")
    with pytest.raises(ValueError):
        ctx.register_device_router(APIRouter(), auth=None)


def test_register_rejects_non_callable_auth():
    from hydrahive.modules.context import ModuleContext
    ctx = ModuleContext("x")
    with pytest.raises(ValueError):
        ctx.register_device_router(APIRouter(), auth="geheim")


def test_device_route_reachable_without_login(dev_app):
    r = TestClient(dev_app).post("/api/module-device/rigs/report", headers={"X-Device-Token": "good"})
    assert r.status_code == 200
    assert r.json() == {"stored": True}


def test_device_route_wrong_token_rejected(dev_app):
    c = TestClient(dev_app)
    assert c.post("/api/module-device/rigs/report", headers={"X-Device-Token": "bad"}).status_code == 401
    assert c.post("/api/module-device/rigs/report").status_code == 401


def test_device_route_not_under_login_prefix(dev_app):
    """Der Geräte-Router hängt NICHT unter /api/modules/<id> (keine Vermischung)."""
    r = TestClient(dev_app).post("/api/modules/rigs/report", headers={"X-Device-Token": "good"})
    assert r.status_code in (401, 404)
    assert r.status_code != 200


def test_normal_module_router_still_needs_login(dev_app):
    assert TestClient(dev_app).get("/api/modules/rigs/ping").status_code == 401


def test_device_route_rate_limited(dev_app, monkeypatch):
    from hydrahive.api import module_devices
    monkeypatch.setattr(module_devices, "DEVICE_RATE_LIMIT", 3)
    c = TestClient(dev_app)
    codes = [c.post("/api/module-device/rigs/report", headers={"X-Device-Token": "good"}).status_code
             for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3] == 429


def test_rate_limit_counts_failed_attempts(dev_app, monkeypatch):
    """Auch falsche Tokens zählen — sonst wäre Durchprobieren unbegrenzt."""
    from hydrahive.api import module_devices
    monkeypatch.setattr(module_devices, "DEVICE_RATE_LIMIT", 2)
    c = TestClient(dev_app)
    codes = [c.post("/api/module-device/rigs/report", headers={"X-Device-Token": "x"}).status_code
             for _ in range(3)]
    assert codes == [401, 401, 429]
