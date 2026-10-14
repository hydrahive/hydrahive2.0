"""Lokale Kopie löschen: Route, Liste, Platz, Abgleich, Umzug (Spec archiv-system.md, Etappe 3b)."""
from __future__ import annotations

import pytest

from tests.conftest import error_code

pytest_plugins = ["tests._delete_env", "tests._remote_env", "tests._drop_env"]

URL = "/api/admin/archive/entries/drop-local"


def _dropped(drop_jobs, client, admin_headers, body: dict) -> dict:
    r = client.post(URL, headers=admin_headers, json=body)
    assert r.status_code == 202, r.text
    drop_jobs.process_queue()
    return r.json()


def test_route_needs_admin_and_active_server(client, auth_headers, admin_headers, archive_root, fake_remote,
                                             remote_queue, drop_jobs) -> None:
    assert client.post(URL, headers=auth_headers, json={"all_verified": True}).status_code == 403
    r = client.post(URL, headers=admin_headers, json={"all_verified": True})
    assert r.status_code == 409 and error_code(r) == "archive_remote_inactive"


@pytest.mark.parametrize("path", ["../geheim.tar.gz", "agents/../../x.tar.gz", "/etc/passwd", "agents/hand.zip",
                                  "unbekannt/x.tar.gz", "agents/a/b.tar.gz", ""])
def test_route_rejects_bad_paths(client, admin_headers, remote_on, drop_jobs, path) -> None:
    r = client.post(URL, headers=admin_headers, json={"paths": [path]})
    assert r.status_code == 400 and error_code(r) == "archive_path_invalid"
    assert drop_jobs.list_jobs()["queued"] == []


def test_route_rejects_nothing_selected(client, admin_headers, remote_on, drop_jobs) -> None:
    r = client.post(URL, headers=admin_headers, json={"paths": []})
    assert r.status_code == 400 and error_code(r) == "archive_nothing_selected"


def test_route_rejects_packages_not_on_server(client, admin_headers, archive_root, remote_on, remote_queue,
                                              on_server, drop_jobs) -> None:
    [ok] = on_server(1)
    from hydrahive.archive import deletion
    from tests._delete_fixtures import make_agent, packages
    deletion.run("agent", make_agent("Noch nicht oben")["id"], "archive", actor="admin")
    [waiting] = [f"agents/{p.name}" for p in packages(archive_root, "agents") if f"agents/{p.name}" != ok]

    r = client.post(URL, headers=admin_headers, json={"paths": [ok, waiting]})

    assert r.status_code == 409 and error_code(r) == "archive_not_on_server"
    assert drop_jobs.list_jobs()["queued"] == [] and (archive_root / ok).exists()


def test_all_verified_takes_only_packages_on_the_server(client, admin_headers, archive_root, remote_on,
                                                        remote_queue, on_server, drop_jobs) -> None:
    rels = on_server(2)
    hand = archive_root / "uploads" / "hand.pdf"
    hand.parent.mkdir(parents=True, exist_ok=True)
    hand.write_bytes(b"%PDF")
    remote_queue.sync()
    remote_queue.process_queue()                                 # von Hand Abgelegtes liegt auch oben …

    body = _dropped(drop_jobs, client, admin_headers, {"all_verified": True})

    assert body["job_id"] and body["count"] == 2
    assert not any((archive_root / r).exists() for r in rels)
    assert hand.exists()                                         # … bleibt aber hier (Till, 14.10.)


def test_all_verified_with_nothing_to_do(client, admin_headers, remote_on, drop_jobs) -> None:
    r = client.post(URL, headers=admin_headers, json={"all_verified": True})
    assert r.status_code == 400 and error_code(r) == "archive_nothing_selected"


def test_list_status_and_space_after_drop(client, admin_headers, archive_root, remote_on, on_server,
                                          drop_jobs) -> None:
    keep, drop = on_server(2)
    before = client.get("/api/admin/archive/status", headers=admin_headers).json()
    size = (archive_root / drop).stat().st_size

    _dropped(drop_jobs, client, admin_headers, {"paths": [drop]})

    entries = {e["path"]: e for e in client.get("/api/admin/archive/entries", headers=admin_headers).json()["entries"]}
    assert entries[drop]["local"] is False and entries[drop]["remote"]["state"] == "remote_only"
    assert entries[drop]["size"] == size                         # Größe des Pakets, auch wenn es nur oben liegt
    assert entries[keep]["local"] is True
    after = client.get("/api/admin/archive/status", headers=admin_headers).json()
    assert after["storage"]["count"] == before["storage"]["count"]
    assert after["storage"]["used_bytes"] == before["storage"]["used_bytes"] - size
    assert after["remote"]["on_server"] == before["remote"]["on_server"]
    assert after["remote"]["remote_only"] == 1 and after["remote"]["local_only"] == 0
    assert after["remote"]["droppable"] == 1
    assert after["remote"]["droppable_bytes"] == (archive_root / keep).stat().st_size


def test_sync_leaves_server_only_packages_alone(archive_root, remote_on, remote_queue, on_server,
                                                drop_jobs) -> None:
    from hydrahive.archive import drop_local
    [rel] = on_server(1)
    drop_local.submit(paths=[rel], actor="admin")
    drop_jobs.process_queue()
    puts = remote_on.puts

    assert remote_queue.sync() == 0
    remote_queue.process_queue()
    assert remote_on.puts == puts and not (archive_root / rel).exists()


def test_move_takes_the_json_of_server_only_packages_along(archive_root, remote_on, on_server, drop_jobs,
                                                           tmp_path) -> None:
    from hydrahive.archive import drop_local, move
    [rel] = on_server(1)
    drop_local.submit(paths=[rel], actor="admin")
    drop_jobs.process_queue()
    target = tmp_path / "neue-platte" / "archiv"

    assert move.run_move(target)["state"] == "done"

    assert (target / (rel + ".json")).exists() and not (target / rel).exists()
