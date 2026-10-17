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


# --- Abläufe laufen zu Ende, auch ohne Leser (docs/specs/modul-update-unabhaengig-vom-browser.md) ---

def _wait_free(timeout: float = 5.0) -> None:
    from hydrahive.modules import operations
    op = operations.current()
    if op is not None:
        assert op.wait(timeout)


def test_update_stream_format_unchanged(client, admin_headers):
    with patch("hydrahive.api.routes.modules.installer.update", return_value=iter(["a", "b"])):
        r = client.post("/api/admin/modules/example/update", headers=admin_headers)
    _wait_free()
    assert r.status_code == 200
    assert r.text == 'data: {"line": "a"}\n\ndata: {"line": "b"}\n\ndata: {"done": true}\n\n'


def test_update_error_keeps_format(client, admin_headers):
    def boom():
        yield "a"
        raise RuntimeError("kaputt")
    with patch("hydrahive.api.routes.modules.installer.update", return_value=boom()):
        r = client.post("/api/admin/modules/example/update", headers=admin_headers)
    _wait_free()
    assert r.text.endswith('data: {"error": "kaputt"}\n\n')


def test_busy_returns_409(client, admin_headers):
    import threading
    from hydrahive.modules import operations
    gate = threading.Event()

    def slow():
        yield "läuft"
        assert gate.wait(5)
    op = operations.start("update", "studio", slow())
    try:
        r = client.post("/api/admin/modules/example/install", headers=admin_headers)
        assert r.status_code == 409
        assert r.json()["detail"]["code"] == "module_operation_busy"
        assert r.json()["detail"]["params"]["module"] == "studio"
    finally:
        gate.set()
        assert op.wait(5)


def test_route_runs_to_the_end_when_client_leaves(setup_test_env):
    """Die Route selbst: erste Zeile lesen, dann den Stream schließen (so trennt der Server einen gegangenen Browser)."""
    import asyncio
    import threading
    from hydrahive.api.routes import modules as routes
    from hydrahive.modules import operations
    reached: list[str] = []
    gate = threading.Event()

    def gen():
        reached.append("ersetzt"); yield "Dateien ersetzt"
        assert gate.wait(5)
        reached.append("gebaut"); yield "Frontend gebaut"
        reached.append("neustart"); yield "Neustart angefordert"

    async def read_first_then_leave() -> str:
        resp = routes.update_module("example")
        body = resp.body_iterator
        first = await body.__anext__()
        await body.aclose()                              # Browser ist weg
        return first if isinstance(first, str) else first.decode()

    with patch("hydrahive.api.routes.modules.installer.update", return_value=gen()):
        first = asyncio.run(read_first_then_leave())
        op = operations.current()
        gate.set()
        if op is not None:
            assert op.wait(5)
    assert "Dateien ersetzt" in first
    assert reached == ["ersetzt", "gebaut", "neustart"]
