"""Modul-Routen: Abläufe laufen ohne Leser zu Ende, nur einer gleichzeitig (docs/specs/modul-update-unabhaengig-vom-browser.md)."""
from __future__ import annotations

from unittest.mock import patch

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


def test_each_route_starts_its_own_kind(setup_test_env):
    """Install, Update und Deinstallation laufen als eigene Art (steht im 409 eines zweiten Starts)."""
    import asyncio
    import threading
    from hydrahive.api.routes import modules as routes
    from hydrahive.modules import operations
    for route, target, kind in [(routes.install_module, "install", "install"), (routes.update_module, "update", "update"),
                                (routes.uninstall_module, "uninstall", "uninstall")]:
        gate = threading.Event()

        def slow(g=gate):
            yield "läuft"
            assert g.wait(5)
        with patch(f"hydrahive.api.routes.modules.installer.{target}", return_value=slow()):
            resp = route("example")
            op = operations.current()
            assert op is not None and (op.kind, op.module_id) == (kind, "example"), kind
            gate.set()
            assert op.wait(5)
            asyncio.run(resp.body_iterator.aclose())


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
