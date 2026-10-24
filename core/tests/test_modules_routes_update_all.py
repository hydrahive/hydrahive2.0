"""docs/specs/modul-update-alle.md: Route POST /api/admin/modules/update-all (SSE, nur Admin, ein Ablauf zur Zeit)."""
from __future__ import annotations

import threading
from unittest.mock import patch


def _wait_free(timeout: float = 5.0) -> None:
    from hydrahive.modules import operations
    op = operations.current()
    if op is not None:
        assert op.wait(timeout)


def test_update_all_streamt_im_ueblichen_format(client, admin_headers):
    with patch("hydrahive.api.routes.modules.installer.update_all", return_value=iter(["a", "b"])) as ua, \
         patch("hydrahive.api.routes.modules.installer.update") as single:
        r = client.post("/api/admin/modules/update-all", headers=admin_headers)
    _wait_free()
    assert r.status_code == 200
    assert r.text == 'data: {"line": "a"}\n\ndata: {"line": "b"}\n\ndata: {"done": true}\n\n'
    ua.assert_called_once_with()
    single.assert_not_called()          # „update-all“ ist keine Modul-ID


def test_update_all_fehler_im_ablauf(client, admin_headers):
    def boom():
        yield "a"
        raise RuntimeError("module_update_all_failed: x (kaputt)")
    with patch("hydrahive.api.routes.modules.installer.update_all", return_value=boom()):
        r = client.post("/api/admin/modules/update-all", headers=admin_headers)
    _wait_free()
    assert r.text.endswith('data: {"error": "module_update_all_failed: x (kaputt)"}\n\n')


def test_update_all_nur_admin(client, auth_headers):
    with patch("hydrahive.api.routes.modules.installer.update_all") as ua:
        assert client.post("/api/admin/modules/update-all").status_code == 401
        assert client.post("/api/admin/modules/update-all", headers=auth_headers).status_code == 403
    ua.assert_not_called()


def test_update_all_409_wenn_schon_ein_ablauf_laeuft(client, admin_headers):
    from hydrahive.modules import operations
    gate = threading.Event()

    def slow():
        yield "läuft"
        assert gate.wait(5)
    op = operations.start("update", "studio", slow())
    try:
        with patch("hydrahive.api.routes.modules.installer.update_all") as ua:
            r = client.post("/api/admin/modules/update-all", headers=admin_headers)
        assert r.status_code == 409
        assert r.json()["detail"]["code"] == "module_operation_busy"
        ua.assert_not_called()
    finally:
        gate.set()
        assert op.wait(5)


def test_update_all_laeuft_als_eigene_art(setup_test_env):
    import asyncio
    from hydrahive.api.routes import modules as routes
    from hydrahive.modules import operations
    gate = threading.Event()

    def slow():
        yield "läuft"
        assert gate.wait(5)
    with patch("hydrahive.api.routes.modules.installer.update_all", return_value=slow()):
        resp = routes.update_all_modules()
        op = operations.current()
        assert op is not None and (op.kind, op.module_id) == ("update-all", "*")
        gate.set()
        assert op.wait(5)
        asyncio.run(resp.body_iterator.aclose())
