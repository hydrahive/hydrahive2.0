"""API des System-Archivs für das Admin-Fenster (Spec archiv-system.md, Etappe 1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.archive import package
from hydrahive.settings import settings


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    from hydrahive.archive import location
    r = tmp_path / "archiv"
    monkeypatch.setattr(location, "archive_root", lambda: r)
    return r


@pytest.fixture
def packed(root: Path, tmp_path: Path) -> dict:
    src = tmp_path / "q"
    src.mkdir()
    (src / "a.txt").write_text("x")
    return package.pack(kind="agents", name="Alter Agent", source_id="0450556d", owner="till",
                        reason="agent_deleted", sources=[("ws", src)])


@pytest.fixture
def samba(monkeypatch):
    from hydrahive.api.routes import archive as route
    monkeypatch.setattr(route, "samba_status", lambda: {
        "installed": True, "running": True, "password_set": True, "user": "hh",
        "includes_dir": "/etc/samba/hh-projects.d", "includes_dir_exists": True,
    })
    monkeypatch.setattr(route, "_read_samba_password", lambda: "geheim-123")
    monkeypatch.setattr(route, "archive_share_enabled", lambda: True)
    monkeypatch.setattr(route.setup, "ensure_archive", lambda: {"folder": True, "share": "on"})
    return route


@pytest.mark.parametrize("method,url", [
    ("get", "/api/admin/archive/status"),
    ("get", "/api/admin/archive/entries"),
    ("post", "/api/admin/archive/trash/empty"),
    ("put", "/api/admin/archive/share"),
])
def test_admin_only(client, auth_headers, method, url) -> None:
    body = {"post": {"confirm": "Papierkorb"}, "put": {"enabled": False}}.get(method)
    r = getattr(client, method)(url, headers=auth_headers, **({"json": body} if body else {}))
    assert r.status_code == 403


def test_status_shows_location_and_share(client, admin_headers, root, packed, samba) -> None:
    r = client.get("/api/admin/archive/status", headers=admin_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["target"] == "local"
    assert body["storage"]["path"] == str(root) and body["storage"]["count"] == 1
    assert body["storage"]["by_kind"] == {"agents": 1}
    share = body["share"]
    assert share["name"] == "HydraHive_Archiv" and share["enabled"] is True
    assert share["login"] == "hh" and share["password"] == "geheim-123"
    assert share["samba_installed"] is True


def test_status_without_samba(client, admin_headers, root, monkeypatch) -> None:
    from hydrahive.api.routes import archive as route
    monkeypatch.setattr(route, "samba_status", lambda: {
        "installed": False, "running": False, "password_set": False, "user": "hh",
        "includes_dir": "/x", "includes_dir_exists": False,
    })
    monkeypatch.setattr(route, "archive_share_enabled", lambda: False)
    monkeypatch.setattr(route.setup, "ensure_archive", lambda: {"folder": True, "share": "no_samba"})

    share = client.get("/api/admin/archive/status", headers=admin_headers).json()["share"]

    assert share["samba_installed"] is False and share["enabled"] is False
    assert share["password"] == ""


def test_share_enabled_reads_share_file(tmp_path, monkeypatch) -> None:
    from hydrahive.archive import share
    monkeypatch.setattr(settings, "samba_includes_dir", tmp_path, raising=False)

    assert share.archive_share_enabled() is False
    (tmp_path / "_system-archiv.conf").write_text("[HydraHive_Archiv]\n")
    assert share.archive_share_enabled() is True


def test_status_runs_setup_and_reports_disk(client, admin_headers, root, samba, monkeypatch) -> None:
    """Status richtet das Archiv ein (ohne Installer) und meldet Platte und Freigabe-Wunsch."""
    from hydrahive.api.routes import archive as route
    calls = []
    monkeypatch.setattr(route.setup, "ensure_archive", lambda: calls.append(1) or {"folder": True, "share": "on"})

    body = client.get("/api/admin/archive/status", headers=admin_headers).json()

    assert calls == [1]
    assert body["share"]["wanted"] is True
    assert body["storage"]["is_default"] is False          # Fixture legt das Archiv woanders hin
    assert body["storage"]["mount"] and Path(body["storage"]["mount"]).is_dir()

    from hydrahive.archive import location
    monkeypatch.setattr(location, "is_default", lambda: True)
    assert client.get("/api/admin/archive/status", headers=admin_headers).json()["storage"]["is_default"] is True


def test_share_switch(client, admin_headers, root, samba, monkeypatch) -> None:
    from hydrahive.api.routes import archive as route
    from hydrahive.archive import location
    state = {"wanted": True}
    monkeypatch.setattr(location, "set_share_wanted", lambda v: state.__setitem__("wanted", v))
    monkeypatch.setattr(location, "share_wanted", lambda: state["wanted"])
    monkeypatch.setattr(route.setup, "ensure_archive", lambda: {"folder": True, "share": "off" if not state["wanted"] else "on"})

    r = client.put("/api/admin/archive/share", headers=admin_headers, json={"enabled": False})

    assert r.status_code == 200 and r.json()["share"] == "off"
    assert state["wanted"] is False
    for bad in ("ja", "false", 0, None):
        assert client.put("/api/admin/archive/share", headers=admin_headers, json={"enabled": bad}).status_code == 422
    assert state["wanted"] is False


def test_entries_list_and_filter(client, admin_headers, root, packed) -> None:
    (root / "uploads").mkdir()
    (root / "uploads" / "hand.zip").write_bytes(b"h")

    all_ = client.get("/api/admin/archive/entries", headers=admin_headers).json()["entries"]
    agents = client.get("/api/admin/archive/entries?kind=agents", headers=admin_headers).json()["entries"]

    assert {e["file"] for e in all_} == {packed["file"], "hand.zip"}
    assert [e["file"] for e in agents] == [packed["file"]]
    assert client.get("/api/admin/archive/entries?kind=../x", headers=admin_headers).status_code == 400


def test_empty_trash_needs_confirm_word(client, admin_headers, root) -> None:
    (root / ".papierkorb").mkdir(parents=True)
    (root / ".papierkorb" / "alt.bin").write_bytes(b"12345")

    bad = client.post("/api/admin/archive/trash/empty", headers=admin_headers, json={"confirm": "ja"})
    assert bad.status_code == 400 and bad.json()["detail"]["code"] == "archive_trash_confirm_required"
    assert (root / ".papierkorb" / "alt.bin").exists()

    ok = client.post("/api/admin/archive/trash/empty", headers=admin_headers, json={"confirm": "Papierkorb"})
    assert ok.status_code == 200 and ok.json()["freed_bytes"] == 5
    assert not (root / ".papierkorb" / "alt.bin").exists()
