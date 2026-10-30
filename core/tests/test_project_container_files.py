"""docs/specs/projekt-container-ausfuehrung.md (K1b): Datei-Werkzeuge in Container-Projekten.

Lesen/Schreiben läuft nur über incus im Container; die Host-Platte (Workspace) bleibt unberührt. Pfade werden IM
Container aufgelöst (realpath), damit Symlinks dort richtig zählen. incus ist eine Attrappe mit einem kleinen
Dateisystem im Speicher.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.tools import _fs, file_patch, file_read, file_write
from hydrahive.tools.base import ToolContext
from tests._fake_container_fs import FakeContainer

_CT = {"mode": "container", "container": "hh-labor-probe", "workdir": "/work", "user": 1000}


@pytest.fixture
def ct(monkeypatch):
    fake = FakeContainer()
    monkeypatch.setattr(_fs, "_incus", fake.run)
    monkeypatch.setattr(_fs, "_INCUS", "incus")
    monkeypatch.setattr(_fs, "_execution", lambda ctx: dict(_CT))
    return fake


@pytest.fixture
def host_ws(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    return ws


def _ctx(ws: Path) -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=ws, project_id="p1")


def _run(mod, args, ctx):
    return asyncio.run(mod._execute(args, ctx))


def test_lesen_aus_dem_container(ct, host_ws):
    res = _run(file_read, {"path": "a.txt"}, _ctx(host_ws))
    assert res.success and "zwei" in res.output
    assert any(c[:3] == ["incus", "exec", "hh-labor-probe"] and "cat" in c for c in ct.calls)


def test_lesen_mit_grep_und_bereich(ct, host_ws):
    assert "     2\tzwei" in _run(file_read, {"path": "/work/a.txt", "grep": "zwei", "context_lines": 0},
                                  _ctx(host_ws)).output
    assert _run(file_read, {"path": "a.txt", "offset": 3, "limit": 1}, _ctx(host_ws)).output == "     3\tdrei"


@pytest.mark.parametrize("path", ["/etc/passwd", "../etc/passwd", "/work/../etc/passwd", "raus/passwd", "pw",
                                  "/", "/work/sub/../../etc/passwd", "/workshop/geheim.txt",
                                  "../workshop/geheim.txt"])
def test_lesen_ausserhalb_abgelehnt(ct, host_ws, path):
    res = _run(file_read, {"path": path}, _ctx(host_ws))
    assert not res.success
    assert not any("cat" in c for c in ct.calls)


def test_schreiben_landet_nur_im_container(ct, host_ws):
    res = _run(file_write, {"path": "sub/neu.py", "content": "print(1)\n"}, _ctx(host_ws))
    assert res.success
    assert ct.files["/work/sub/neu.py"] == b"print(1)\n"
    assert list(host_ws.rglob("*")) == []                          # Host-Workspace unberührt


def test_schreiben_als_nutzer_nicht_als_root(ct, host_ws):
    _run(file_write, {"path": "x.txt", "content": "a"}, _ctx(host_ws))
    w = [c for c in ct.calls if c[1] == "exec" and 'mv -f "$t" "$1"' in " ".join(c)]
    assert w and all(c[c.index("--user") + 1] == "1000" for c in w)


@pytest.mark.parametrize("path", ["/etc/cron.d/x", "../x", "raus/shadow", "/tmp/x", "pw"])
def test_schreiben_ausserhalb_abgelehnt(ct, host_ws, path):
    before = dict(ct.files)
    res = _run(file_write, {"path": path, "content": "boese"}, _ctx(host_ws))
    assert not res.success
    assert ct.files == before


def test_zielpfad_als_ein_argument(ct, host_ws):
    """Ein Pfad mit Sonderzeichen wird nie in einen Shell-Text eingesetzt."""
    name = "sub/a b;$(touch x)`id`.txt"
    _run(file_write, {"path": name, "content": "a"}, _ctx(host_ws))
    w = [c for c in ct.calls if c[1] == "exec" and 'mv -f "$t" "$1"' in " ".join(c)][0]
    script = w[w.index("--") + 3]
    assert "touch" not in script and "`id`" not in script
    assert w[-1] == "/work/sub/a b;$(touch x)`id`.txt"


def test_patch_im_container(ct, host_ws):
    res = _run(file_patch, {"path": "a.txt", "old_string": "zwei", "new_string": "ZWEI"}, _ctx(host_ws))
    assert res.success and ct.files["/work/a.txt"] == b"eins\nZWEI\ndrei\n"
    assert list(host_ws.rglob("*")) == []


def test_patch_ueber_symlink_nach_draussen_abgelehnt(ct, host_ws):
    res = _run(file_patch, {"path": "pw", "old_string": "root", "new_string": "evil"}, _ctx(host_ws))
    assert not res.success and ct.files["/etc/passwd"] == b"root:x:0:0\n"


def test_zu_grosse_datei_wird_nicht_gelesen(ct, host_ws):
    ct.files["/work/gross.bin"] = b"x" * (_fs.MAX_READ_BYTES + 1)
    res = _run(file_read, {"path": "gross.bin"}, _ctx(host_ws))
    assert not res.success


def test_host_projekt_unveraendert(monkeypatch, host_ws):
    """Gegenprobe: ohne Container-Projekt kein incus, Dateien auf der Host-Platte wie bisher."""
    monkeypatch.setattr(_fs, "_incus", lambda *a, **k: pytest.fail("incus bei Host-Projekt"))
    monkeypatch.setattr(_fs, "_execution", lambda ctx: {"mode": "host"})
    ctx = _ctx(host_ws)
    assert _run(file_write, {"path": "h.txt", "content": "host"}, ctx).success
    assert (host_ws / "h.txt").read_text() == "host"
    assert "host" in _run(file_read, {"path": "h.txt"}, ctx).output
    assert _run(file_patch, {"path": "h.txt", "old_string": "host", "new_string": "HOST"}, ctx).success
    assert (host_ws / "h.txt").read_text() == "HOST"


def test_ausfuehrung_unklar_kein_zugriff(monkeypatch, host_ws):
    from hydrahive.tools import _launcher_container

    def boom(ctx):
        raise _launcher_container.ExecutionUnavailable("project_execution_unavailable")

    monkeypatch.setattr(_fs, "_execution", boom)
    monkeypatch.setattr(_fs, "_incus", lambda *a, **k: pytest.fail("kein incus"))
    for mod, args in ((file_read, {"path": "a"}), (file_write, {"path": "a", "content": "x"}),
                      (file_patch, {"path": "a", "old_string": "x", "new_string": "y"})):
        res = _run(mod, args, _ctx(host_ws))
        assert not res.success and "project_execution_unavailable" in (res.error or "")
    assert list(host_ws.rglob("*")) == []


def test_fehler_von_realpath_zaehlt_auch_mit_ausgabe(ct, host_ws):
    ct.realpath_fails = True
    assert not _run(file_read, {"path": "a.txt"}, _ctx(host_ws)).success
    assert not _run(file_write, {"path": "a.txt", "content": "x"}, _ctx(host_ws)).success
    assert ct.files["/work/a.txt"] == b"eins\nzwei\ndrei\n"


def test_lesen_nicht_vorhandener_datei_klare_meldung(ct, host_ws):
    res = _run(file_read, {"path": "fehlt.txt"}, _ctx(host_ws))
    assert not res.success and "nicht gefunden" in (res.error or "")
    assert not any("cat" in c for c in ct.calls)
    res = _run(file_patch, {"path": "fehlt.txt", "old_string": "a", "new_string": "b"}, _ctx(host_ws))
    assert not res.success and "nicht gefunden" in (res.error or "")
    assert "/work/fehlt.txt" not in ct.files


def test_realpath_prueft_existenz_beim_lesen(ct, host_ws):
    _run(file_read, {"path": "a.txt"}, _ctx(host_ws))
    rp = [c for c in ct.calls if "realpath" in c]
    assert rp and rp[0][rp[0].index("realpath") + 1] == "-e"
    ct.calls.clear()
    _run(file_write, {"path": "neu.txt", "content": "x"}, _ctx(host_ws))
    rp = [c for c in ct.calls if "realpath" in c]
    assert rp and rp[0][rp[0].index("realpath") + 1] == "-m"


def test_incus_bekommt_keine_server_umgebung(monkeypatch, host_ws):
    """Auch der echte Aufrufweg (_incus) gibt incus nur PATH mit."""
    seen = {}

    class P:
        returncode = 0

        async def communicate(self, data=None):
            return b"/work/a.txt\n", b""

    async def fake(*a, **k):
        seen["env"] = k.get("env")
        return P()

    monkeypatch.setenv("GH_TOKEN", "ghp_SERVER")
    monkeypatch.setattr(_fs.asyncio, "create_subprocess_exec", fake)
    asyncio.run(_fs._incus(["incus", "exec", "x", "--", "true"], None))
    assert seen["env"] == {"PATH": "/usr/bin:/bin"}
