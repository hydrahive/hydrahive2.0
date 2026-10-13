"""Etappe 1b: API für Ort wechseln (Spec archiv-system.md, „Etappe 1b“). Nur Admin, nur IDs aus der Liste."""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.archive import location, setup
from hydrahive.settings import settings


@pytest.fixture
def env(tmp_path, monkeypatch) -> dict:
    from hydrahive.archive import disks
    ws, cfg = tmp_path / "workspaces", tmp_path / "config"
    ws.mkdir()
    cfg.mkdir()
    monkeypatch.setattr(settings, "workspaces_dir", ws, raising=False)
    monkeypatch.setattr(settings, "config_dir", cfg, raising=False)
    monkeypatch.setattr(settings, "samba_includes_dir", tmp_path / "kein-samba", raising=False)
    setup.ensure_archive()
    platte = tmp_path / "platte"
    platte.mkdir()
    gesperrt = tmp_path / "gesperrt"
    gesperrt.mkdir()
    gesperrt.chmod(0o555)            # wie eine frisch eingehängte Platte, die root gehört
    fake = [
        {"id": "aaaaaaaaaaaa", "mount": str(platte), "path": str(platte / "hydrahive-archiv"), "device": "/dev/sdb1",
         "fstype": "ext4", "size_bytes": 10**12, "free_bytes": 10**11, "writable": True},
        {"id": "bbbbbbbbbbbb", "mount": str(gesperrt), "path": str(gesperrt / "hydrahive-archiv"), "device": "/dev/sdc1",
         "fstype": "ext4", "size_bytes": 10**12, "free_bytes": 10**11, "writable": False},
    ]
    monkeypatch.setattr(disks, "list_disks", lambda: fake)
    trigger = tmp_path / "data" / ".addon_request"
    from hydrahive.api.routes import _addon_request
    monkeypatch.setattr(_addon_request, "trigger_path", lambda: trigger)
    yield {"platte": platte, "trigger": trigger, "cfg": cfg}
    gesperrt.chmod(0o755)


@pytest.mark.parametrize("method,url", [
    ("get", "/api/admin/archive/locations"),
    ("post", "/api/admin/archive/move"),
    ("post", "/api/admin/archive/locations/aaaaaaaaaaaa/prepare"),
])
def test_admin_only(client, auth_headers, env, method, url) -> None:
    r = getattr(client, method)(url, headers=auth_headers, **({"json": {"location": "default"}} if method == "post" else {}))
    assert r.status_code == 403


def test_locations_list_default_first_and_marks_current(client, admin_headers, env) -> None:
    body = client.get("/api/admin/archive/locations", headers=admin_headers).json()
    ids = [e["id"] for e in body["entries"]]
    assert ids == ["default", "aaaaaaaaaaaa", "bbbbbbbbbbbb"]
    default = body["entries"][0]
    assert default["current"] is True and default["path"] == str(location.default_root())
    assert body["entries"][1]["problems"] == []
    assert "target_not_writable" in body["entries"][2]["problems"]


def test_move_starts_in_background_and_finishes(client, admin_headers, env) -> None:
    (location.archive_root() / "uploads" / "x.txt").write_text("x")
    r = client.post("/api/admin/archive/move", headers=admin_headers, json={"location": "aaaaaaaaaaaa"})
    assert r.status_code == 202
    from hydrahive.archive import move_job
    move_job.wait(timeout=10)
    status = client.get("/api/admin/archive/status", headers=admin_headers).json()
    assert status["move"]["running"] is None
    assert status["move"]["last"]["state"] == "done"
    assert location.archive_root() == env["platte"] / "hydrahive-archiv"
    assert (env["platte"] / "hydrahive-archiv" / "uploads" / "x.txt").read_text() == "x"


def test_move_rejects_unknown_ids_and_paths(client, admin_headers, env) -> None:
    for bad in ("../../etc", "/etc", "cccccccccccc", "", "DEFAULT"):
        r = client.post("/api/admin/archive/move", headers=admin_headers, json={"location": bad})
        assert r.status_code in (400, 404), bad
    assert location.is_default()


def test_move_conflict_lists_problems(client, admin_headers, env) -> None:
    r = client.post("/api/admin/archive/move", headers=admin_headers, json={"location": "bbbbbbbbbbbb"})
    assert r.status_code == 409
    assert "target_not_writable" in r.json()["detail"]["params"]["problems"]
    r = client.post("/api/admin/archive/move", headers=admin_headers, json={"location": "default"})
    assert r.status_code == 409 and "same_location" in r.json()["detail"]["params"]["problems"]


def test_prepare_writes_fixed_runner_request(client, admin_headers, env) -> None:
    r = client.post("/api/admin/archive/locations/bbbbbbbbbbbb/prepare", headers=admin_headers)
    assert r.status_code == 202
    assert env["trigger"].read_text() == "prepare-archive bbbbbbbbbbbb\n"
    again = client.post("/api/admin/archive/locations/bbbbbbbbbbbb/prepare", headers=admin_headers)
    assert again.status_code == 409


def test_prepare_only_for_listed_disks(client, admin_headers, env) -> None:
    for bad in ("default", "cccccccccccc", "..%2F..%2Fetc", "aaaaaaaaaaa"):
        r = client.post(f"/api/admin/archive/locations/{bad}/prepare", headers=admin_headers)
        assert r.status_code in (400, 404), bad
    assert not env["trigger"].exists()


def test_running_addon_reports_prepare(env) -> None:
    from hydrahive.api.routes._addon_request import running_addon
    env["trigger"].parent.mkdir(parents=True, exist_ok=True)
    env["trigger"].write_text("prepare-archive bbbbbbbbbbbb\n")
    assert running_addon(env["trigger"]) == "prepare-archive"


def test_prepare_marker_in_path_is_not_a_path(env) -> None:
    assert "/" not in Path(env["trigger"]).name
