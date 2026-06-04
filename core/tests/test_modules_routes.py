"""Admin-API-Tests für /api/admin/modules."""
from __future__ import annotations

from unittest.mock import patch


def test_list_modules_admin(client, admin_headers):
    with patch("hydrahive.api.routes.modules.hub_client.read_hub_index", return_value={"modules": []}):
        r = client.get("/api/admin/modules", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "installed" in body and "available" in body


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
