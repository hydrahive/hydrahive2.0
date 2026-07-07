"""Admin-API-Tests für /api/admin/modules."""
from __future__ import annotations

from unittest.mock import patch


def test_list_modules_admin(client, admin_headers):
    with patch("hydrahive.api.routes.modules.hub_client.refresh"), \
         patch("hydrahive.api.routes.modules.hub_client.read_hub_index", return_value={"modules": []}):
        r = client.get("/api/admin/modules", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "modules" in body and isinstance(body["modules"], list)


def test_list_modules_refreshes_hub(client, admin_headers):
    # Die Liste muss den echten Hub spiegeln → vor dem Listen pullen.
    with patch("hydrahive.api.routes.modules.hub_client.refresh") as mock_refresh, \
         patch("hydrahive.api.routes.modules.hub_client.read_hub_index", return_value={"modules": []}):
        r = client.get("/api/admin/modules", headers=admin_headers)
    assert r.status_code == 200
    mock_refresh.assert_called_once()


def test_list_modules_includes_uninstalled_hub_module(client, admin_headers):
    # Ein Hub-Modul, das NICHT installiert ist, erscheint mit installed=False.
    cached = {"modules": [{"id": "example", "name": "Beispiel", "path": "example"}]}
    with patch("hydrahive.api.routes.modules.REGISTRY", {}), \
         patch("hydrahive.api.routes.modules.hub_client.refresh"), \
         patch("hydrahive.api.routes.modules.hub_client.read_hub_index", return_value=cached), \
         patch("hydrahive.api.routes.modules.installer.available_version", return_value="1.0.0"), \
         patch("hydrahive.api.routes.modules.installer.available_description", return_value="Ein Demo-Modul."):
        r = client.get("/api/admin/modules", headers=admin_headers)
    assert r.status_code == 200
    ex = next(m for m in r.json()["modules"] if m["id"] == "example")
    assert ex["installed"] is False
    assert ex["name"] == "Beispiel"
    assert ex["description"] == "Ein Demo-Modul."


def test_list_modules_refresh_failure_falls_back_to_cache(client, admin_headers):
    # Netzwerk-/Hub-Fehler beim Refresh darf die Liste nicht killen — Cache-Fallback.
    from hydrahive.modules.hub_client import HubError
    cached = {"modules": [{"id": "example", "name": "X", "path": "example"}]}
    with patch("hydrahive.api.routes.modules.REGISTRY", {}), \
         patch("hydrahive.api.routes.modules.hub_client.refresh", side_effect=HubError("net down")), \
         patch("hydrahive.api.routes.modules.hub_client.read_hub_index", return_value=cached), \
         patch("hydrahive.api.routes.modules.installer.available_version", return_value=None), \
         patch("hydrahive.api.routes.modules.installer.available_description", return_value=""):
        r = client.get("/api/admin/modules", headers=admin_headers)
    assert r.status_code == 200
    assert any(m["id"] == "example" for m in r.json()["modules"])


def test_list_modules_requires_admin(client, auth_headers):
    # auth_headers = normaler (kein Admin) User → muss abgelehnt werden
    r = client.get("/api/admin/modules", headers=auth_headers)
    assert r.status_code in (401, 403)


def test_install_streams(client, admin_headers):
    with patch(
        "hydrahive.api.routes.modules.installer.install",
        return_value=iter(["line1", "done"]),
    ):
        r = client.post("/api/admin/modules/example/install", headers=admin_headers)
    assert r.status_code == 200
    assert "line1" in r.text


# --- Update-Erkennung: erweiterte Felder + /update-count -------------------

def _fake_registry(version: str = "1.0.0"):
    """Ein LoadedModule 'demo' mit gegebener installierter Version."""
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.modules.registry import LoadedModule
    from pathlib import Path
    manifest = ModuleManifest(id="demo", name="Demo", version=version)
    return {"demo": LoadedModule(name="demo", manifest=manifest, path=Path("/x"), loaded=True)}


def test_list_modules_marks_update_available(client, admin_headers):
    with patch("hydrahive.api.routes.modules.REGISTRY", _fake_registry("1.0.0")), \
         patch("hydrahive.api.routes.modules.hub_client.refresh"), \
         patch("hydrahive.api.routes.modules.hub_client.read_hub_index", return_value={"modules": []}), \
         patch("hydrahive.api.routes.modules.installer.available_version", return_value="1.2.0"), \
         patch("hydrahive.api.routes.modules.installer.available_description", return_value=""):
        r = client.get("/api/admin/modules", headers=admin_headers)
    assert r.status_code == 200
    demo = next(m for m in r.json()["modules"] if m["id"] == "demo")
    assert demo["installed"] is True
    assert demo["version"] == "1.0.0"
    assert demo["available_version"] == "1.2.0"
    assert demo["update_available"] is True


def test_list_modules_no_update_when_current(client, admin_headers):
    with patch("hydrahive.api.routes.modules.REGISTRY", _fake_registry("2.0.0")), \
         patch("hydrahive.api.routes.modules.hub_client.refresh"), \
         patch("hydrahive.api.routes.modules.hub_client.read_hub_index", return_value={"modules": []}), \
         patch("hydrahive.api.routes.modules.installer.available_version", return_value="2.0.0"), \
         patch("hydrahive.api.routes.modules.installer.available_description", return_value=""):
        r = client.get("/api/admin/modules", headers=admin_headers)
    demo = next(m for m in r.json()["modules"] if m["id"] == "demo")
    assert demo["update_available"] is False


def test_update_count_admin(client, admin_headers):
    with patch("hydrahive.api.routes.modules.REGISTRY", _fake_registry("1.0.0")), \
         patch("hydrahive.api.routes.modules.installer.available_version", return_value="1.5.0"):
        r = client.get("/api/admin/modules/update-count", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_update_count_zero_when_current(client, admin_headers):
    with patch("hydrahive.api.routes.modules.REGISTRY", _fake_registry("1.5.0")), \
         patch("hydrahive.api.routes.modules.installer.available_version", return_value="1.5.0"):
        r = client.get("/api/admin/modules/update-count", headers=admin_headers)
    assert r.json()["count"] == 0


def test_update_count_requires_admin(client, auth_headers):
    r = client.get("/api/admin/modules/update-count", headers=auth_headers)
    assert r.status_code in (401, 403)
