"""Externer Server: Kopier-Reihe und Abgleich (Spec archiv-system.md, Etappe 3)."""
from __future__ import annotations

import json

from hydrahive.archive import deletion
from tests._delete_fixtures import make_agent, only_package

pytest_plugins = ["tests._delete_env", "tests._remote_env"]  # archive_root, fake_remote, remote_queue, remote_on


def _remote_state(pkg) -> dict:
    return json.loads(pkg.with_name(pkg.name + ".json").read_text()).get("remote") or {}


def test_new_package_is_copied_and_verified(archive_root, remote_on, remote_queue) -> None:
    a = make_agent("Kopie A")
    assert deletion.run("agent", a["id"], "archive", actor="admin")["state"] == "done"
    pkg = only_package(archive_root, "agents")

    remote_queue.process_queue()

    on_nas = remote_on.root / "hydrahive" / "agents" / pkg.name
    assert on_nas.read_bytes() == pkg.read_bytes()
    assert (on_nas.with_name(pkg.name + ".json")).exists()
    st = _remote_state(pkg)
    assert st["state"] == "verified" and st["sha256"] and st["verified_at"]


def test_deleting_never_waits_for_the_nas(archive_root, remote_on, remote_queue) -> None:
    remote_on.down = True
    a = make_agent("Kopie B")
    result = deletion.run("agent", a["id"], "archive", actor="admin")
    assert result["state"] == "done" and result["error"] is None

    remote_queue.process_queue()

    pkg = only_package(archive_root, "agents")
    assert _remote_state(pkg)["state"] == "pending"
    s = remote_queue.summary()
    assert s["waiting"] == 1 and s["last_error"] == "unreachable" and s["next_try_in_s"] >= 60


def test_retry_backoff_and_later_success(archive_root, remote_on, remote_queue, monkeypatch) -> None:
    clock = {"t": 1000.0}
    monkeypatch.setattr(remote_queue, "_now", lambda: clock["t"])
    remote_on.down = True
    a = make_agent("Kopie C")
    deletion.run("agent", a["id"], "archive", actor="admin")
    waits = []
    for _ in range(4):
        remote_queue.process_queue()
        waits.append(remote_queue.summary()["next_try_in_s"])
        clock["t"] += waits[-1]
    assert waits == [60, 300, 1800, 3600]

    remote_on.down = False
    remote_queue.process_queue()
    assert _remote_state(only_package(archive_root, "agents"))["state"] == "verified"
    assert remote_queue.summary()["waiting"] == 0


def test_corrupt_upload_is_not_counted_and_retried(archive_root, remote_on, remote_queue, monkeypatch) -> None:
    clock = {"t": 1000.0}
    monkeypatch.setattr(remote_queue, "_now", lambda: clock["t"])
    remote_on.corrupt = True
    a = make_agent("Kopie D")
    deletion.run("agent", a["id"], "archive", actor="admin")

    remote_queue.process_queue()
    pkg = only_package(archive_root, "agents")
    assert _remote_state(pkg)["state"] == "pending" and remote_queue.summary()["last_error"] == "verify_failed"

    clock["t"] += 3600
    remote_queue.process_queue()
    assert _remote_state(pkg)["state"] == "verified"


def test_nothing_is_queued_while_inactive(archive_root, fake_remote, remote_queue) -> None:
    a = make_agent("Kopie E")
    deletion.run("agent", a["id"], "archive", actor="admin")
    remote_queue.process_queue()
    assert fake_remote.puts == 0 and remote_queue.summary()["waiting"] == 0


def test_sync_picks_up_old_and_manual_files(archive_root, fake_remote, remote_queue) -> None:
    """Pakete von vor dem Eintragen und von Hand abgelegte Dateien kommen mit dem Abgleich hoch."""
    from hydrahive.archive import remote_config
    a = make_agent("Alt F")
    deletion.run("agent", a["id"], "archive", actor="admin")
    (archive_root / "uploads").mkdir(parents=True, exist_ok=True)
    (archive_root / "uploads" / "handablage.pdf").write_bytes(b"%PDF von Hand")
    (archive_root / ".papierkorb").mkdir(exist_ok=True)
    (archive_root / ".papierkorb" / "weg.txt").write_text("nicht hochladen")
    remote_config.save({"host": "nas.local", "share": "Backups", "subdir": "", "user": "hh", "password": "x"})
    remote_config.mark_tested(remote_config.fingerprint())
    remote_config.set_active(True)

    queued = remote_queue.sync()
    remote_queue.process_queue()

    assert queued == 2
    assert (fake_remote.root / "uploads" / "handablage.pdf").read_bytes() == b"%PDF von Hand"
    assert (fake_remote.root / "agents" / only_package(archive_root, "agents").name).exists()
    assert not any(p.name == "weg.txt" for p in fake_remote.root.rglob("*"))
    assert remote_queue.sync() == 0                             # zweiter Abgleich: alles schon da
    remote_config.reset_for_tests()


def test_restart_mid_upload_keeps_queue(archive_root, remote_on, remote_queue, monkeypatch) -> None:
    class _Crash(BaseException):
        pass

    a = make_agent("Neustart G")
    deletion.run("agent", a["id"], "archive", actor="admin")
    real = remote_on.put

    def crash(rel, local):
        part = remote_on.root / (rel + ".part")
        part.parent.mkdir(parents=True, exist_ok=True)
        part.write_bytes(b"halb")
        raise _Crash()

    monkeypatch.setattr(remote_on, "put", crash)
    try:
        remote_queue.process_queue()
    except _Crash:
        pass
    remote_queue.reload_for_tests()                        # wie nach einem Neustart: Zustand von der Platte
    monkeypatch.setattr(remote_on, "put", real)
    remote_queue.process_queue()

    pkg = only_package(archive_root, "agents")
    assert _remote_state(pkg)["state"] == "verified"
    assert (remote_on.root / "hydrahive" / "agents" / pkg.name).read_bytes() == pkg.read_bytes()


def test_status_shows_remote_counts(client, admin_headers, archive_root, remote_on, remote_queue) -> None:
    a = make_agent("Status H")
    deletion.run("agent", a["id"], "archive", actor="admin")
    s = client.get("/api/admin/archive/status", headers=admin_headers).json()["remote"]
    assert s["active"] is True and s["waiting"] == 1
    remote_queue.process_queue()
    s = client.get("/api/admin/archive/status", headers=admin_headers).json()["remote"]
    assert s["waiting"] == 0 and s["on_server"] >= 1
    entry = client.get("/api/admin/archive/entries", headers=admin_headers).json()["entries"][0]
    assert entry["remote"]["state"] == "verified"
    r = client.post("/api/admin/archive/remote/sync", headers=admin_headers)
    assert r.status_code == 202 and r.json()["queued"] == 0
