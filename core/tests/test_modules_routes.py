"""Admin-API-Tests für /api/admin/modules."""
from __future__ import annotations

from unittest.mock import patch


def test_list_modules_admin(client, admin_headers):
    with patch("hydrahive.api.routes.modules.hub_client.refresh"), \
         patch("hydrahive.api.routes.modules.hub_client.read_hub_index", return_value={"modules": []}):
        r = client.get("/api/admin/modules", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "installed" in body and "available" in body


def test_list_modules_refreshes_hub(client, admin_headers):
    # Die "available"-Liste muss den echten Hub spiegeln → vor dem Listen pullen.
    with patch("hydrahive.api.routes.modules.hub_client.refresh") as mock_refresh, \
         patch("hydrahive.api.routes.modules.hub_client.read_hub_index", return_value={"modules": []}):
        r = client.get("/api/admin/modules", headers=admin_headers)
    assert r.status_code == 200
    mock_refresh.assert_called_once()


def test_list_modules_refresh_failure_falls_back_to_cache(client, admin_headers):
    # Netzwerk-/Hub-Fehler beim Refresh darf die Liste nicht killen — Cache-Fallback.
    from hydrahive.modules.hub_client import HubError
    cached = {"modules": [{"id": "example", "name": "X", "path": "example"}]}
    with patch("hydrahive.api.routes.modules.hub_client.refresh", side_effect=HubError("net down")), \
         patch("hydrahive.api.routes.modules.hub_client.read_hub_index", return_value=cached):
        r = client.get("/api/admin/modules", headers=admin_headers)
    assert r.status_code == 200
    assert any(m["id"] == "example" for m in r.json()["available"])


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
