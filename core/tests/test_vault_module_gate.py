"""Vault-Sperre am Modul-Tor und an den Zugangsdaten (docs/specs/vault.md §4.1).

Module mit ``"vault": true`` im Manifest sind ohne Entsperrung 423; andere Module unverändert.
Geräte-Routen (/api/module-device/…) bleiben frei. Die Seite Zugangsdaten (/api/credentials) ist gesperrt.
"""
from __future__ import annotations

import json
import time

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from tests.conftest import error_code


def _manifest(tmp_path, mid: str, vault: bool):
    from hydrahive.modules.manifest import ModuleManifest
    p = tmp_path / f"{mid}.json"
    p.write_text(json.dumps({"id": mid, "name": mid, "version": "1.0.0", "vault": vault}))
    return ModuleManifest.load(p)


def test_manifest_feld_vault(tmp_path):
    assert _manifest(tmp_path, "a", True).vault is True
    assert _manifest(tmp_path, "b", False).vault is False
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"id": "c", "name": "c", "version": "1.0.0"}))
    from hydrahive.modules.manifest import ModuleManifest
    assert ModuleManifest.load(p).vault is False


@pytest.mark.parametrize("wert", ["true", "yes", 1, [1]])
def test_manifest_vault_nur_echtes_true(tmp_path, wert):
    """Nur JSON-true schaltet den Vault ein – kein „irgendwie wahr“ (Tippfehler sollen nicht sperren/entsperren)."""
    from hydrahive.modules.manifest import ModuleManifest
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"id": "d", "name": "d", "version": "1.0.0", "vault": wert}))
    assert ModuleManifest.load(p).vault is False


def _app_with_modules(tmp_path, monkeypatch, mods: dict[str, bool]) -> FastAPI:
    """Fake-Registry mit Modulen (id → vault) und je einer Route /ping + Geräte-Route /dev."""
    from types import SimpleNamespace

    from hydrahive.api import main as api_main
    from hydrahive.api import module_devices
    from hydrahive.modules import registry
    fake = {}
    for mid, vault in mods.items():
        r = APIRouter()
        r.add_api_route("/ping", lambda: {"ok": True}, methods=["GET"])
        dev = APIRouter()
        dev.add_api_route("/dev", lambda: {"ok": True}, methods=["GET"])
        ctx = SimpleNamespace(routers=[r], device_routers=[(dev, lambda: None)])
        fake[mid] = SimpleNamespace(loaded=True, ctx=ctx, manifest=_manifest(tmp_path, mid, vault))
    monkeypatch.setattr(registry, "REGISTRY", fake)
    monkeypatch.setattr(api_main._modules, "REGISTRY", fake)
    monkeypatch.setattr(module_devices, "REGISTRY", fake)
    app = FastAPI()
    api_main.mount_module_routers(app)
    return app


def _token(uid):
    from hydrahive.vault import pins, tokens
    return tokens.issue(uid, generation=pins.generation(uid), now=time.time())


@pytest.fixture
def uid(client, admin_headers):
    from hydrahive.vault import pins
    u = next(x["user_id"] for x in client.get("/api/users", headers=admin_headers).json() if x["username"] == "testuser")
    pins.set_pin(u, "135790")
    yield u
    pins.reset(u)


def test_vault_modul_gesperrt_andere_offen(client, auth_headers, uid, tmp_path, monkeypatch):
    app = TestClient(_app_with_modules(tmp_path, monkeypatch, {"akte": True, "notiz": False}))
    r = app.get("/api/modules/akte/ping", headers=auth_headers)
    assert r.status_code == 423 and error_code(r) == "vault_locked"
    assert app.get("/api/modules/notiz/ping", headers=auth_headers).status_code == 200
    ok = app.get("/api/modules/akte/ping", headers={**auth_headers, "X-HH-Vault": _token(uid)})
    assert ok.status_code == 200


def test_geraete_route_eines_vault_moduls_bleibt_frei(client, uid, tmp_path, monkeypatch):
    app = TestClient(_app_with_modules(tmp_path, monkeypatch, {"akte": True}))
    assert app.get("/api/module-device/akte/dev").status_code == 200


def test_zugangsdaten_gesperrt(client, auth_headers, uid):
    r = client.get("/api/credentials", headers=auth_headers)
    assert r.status_code == 423 and error_code(r) == "vault_locked"
    assert client.get("/api/credentials", headers={**auth_headers, "X-HH-Vault": _token(uid)}).status_code == 200


def test_zugangsdaten_per_api_key_ohne_pin(client, auth_headers, uid):
    key = client.post("/api/auth/apikeys", json={"name": "cred"}, headers=auth_headers).json()["key"]
    assert client.get("/api/credentials", headers={"Authorization": f"Bearer {key}"}).status_code == 200


def test_agent_werkzeug_nutzt_zugangsdaten_ohne_pin(client, uid, tmp_path):
    """fetch_url & Co. lesen den Store direkt – nicht über die gesperrte Route (Spec §8 Frage 2)."""
    from hydrahive.credentials import store
    assert callable(store.match_credential)
    from hydrahive.vault import pins
    assert pins.is_set(uid)
    store.match_credential("testuser", "https://example.org/x")        # darf nicht an der PIN scheitern
