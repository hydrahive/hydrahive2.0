"""Lokale Kopie löschen: Ablauf, Prüfung vor dem Löschen, Neustart (Spec archiv-system.md, Etappe 3b)."""
from __future__ import annotations

import json

import pytest

from hydrahive.archive import drop_local

pytest_plugins = ["tests._delete_env", "tests._remote_env", "tests._drop_env"]


class _Crash(BaseException):
    """Stellt einen Absturz/Neustart nach: wird von keinem `except Exception` gefangen."""


def _meta(archive_root, rel: str) -> dict:
    return json.loads((archive_root / (rel + ".json")).read_text())


def _on_nas(remote_on, rel: str):
    return remote_on.root / "hydrahive" / rel


def _job(jobs, job_id: str) -> dict:
    [job] = [j for j in jobs.list_jobs()["done"] if j["id"] == job_id]
    return job


def test_reads_back_from_server_then_removes_local_copy(archive_root, remote_on, on_server, drop_jobs,
                                                         monkeypatch) -> None:
    keep, drop = on_server(2)
    size = (archive_root / drop).stat().st_size
    reads = []
    real = remote_on.read_chunks
    monkeypatch.setattr(remote_on, "read_chunks", lambda rel: (reads.append(rel), real(rel))[1])

    job_id = drop_local.submit(paths=[drop], actor="admin")
    drop_jobs.process_queue()

    assert drop in reads                                         # ganz zurückgelesen, nicht nur die Größe
    assert not (archive_root / drop).exists() and (archive_root / keep).exists()
    remote = _meta(archive_root, drop)["remote"]
    assert remote["state"] == "remote_only" and remote["sha256"] == _meta(archive_root, drop)["sha256"]
    assert _on_nas(remote_on, drop).exists()                     # auf dem Server bleibt alles
    job = _job(drop_jobs, job_id)
    assert job["kind"] == "drop_local" and job["state"] == "done" and job["error"] is None
    assert job["done_paths"] == [drop] and job["kept"] == [] and job["freed_bytes"] == size


@pytest.mark.parametrize("damage", ["content", "missing", "server_json"])
def test_bad_server_copy_keeps_local_and_copies_again(archive_root, remote_on, on_server, drop_jobs,
                                                      remote_queue, damage) -> None:
    bad, good = on_server(2)
    nas = _on_nas(remote_on, bad)
    if damage == "content":
        data = nas.read_bytes()
        nas.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))       # gleiche Größe, anderer Inhalt
    elif damage == "missing":
        nas.unlink()
    else:
        meta = nas.with_name(nas.name + ".json")
        meta.write_text(json.dumps({**json.loads(meta.read_text()), "sha256": "0" * 64}))

    job_id = drop_local.submit(paths=[bad, good], actor="admin")
    drop_jobs.process_queue()

    assert (archive_root / bad).exists() and not (archive_root / good).exists()
    assert _meta(archive_root, bad)["remote"]["state"] == "pending"
    assert remote_queue.summary()["waiting"] == 1
    job = _job(drop_jobs, job_id)
    assert job["state"] == "done" and job["done_paths"] == [good]
    assert job["kept"] == [{"path": bad, "reason": "not_found" if damage == "missing" else "verify_failed"}]

    remote_queue.process_queue()                                 # neu hochgeladen → wieder „auf dem Server“
    assert _meta(archive_root, bad)["remote"]["state"] == "verified"


def test_server_unreachable_at_start_deletes_nothing(archive_root, remote_on, on_server, drop_jobs) -> None:
    [rel] = on_server(1)
    remote_on.down = True

    job_id = drop_local.submit(paths=[rel], actor="admin")
    drop_jobs.process_queue()

    assert (archive_root / rel).exists() and _meta(archive_root, rel)["remote"]["state"] == "verified"
    job = _job(drop_jobs, job_id)
    assert job["state"] == "failed" and job["error"] == "unreachable" and job["done_paths"] == []


def test_package_no_longer_verified_when_the_job_runs_is_kept(archive_root, remote_on, on_server,
                                                               drop_jobs) -> None:
    """Zwischen Einreihen und Ausführen kann sich der Stand ändern (z. B. neu eingereiht): dann nicht anfassen."""
    from hydrahive.archive import _remote_files as rf
    [rel] = on_server(1)
    job_id = drop_local.submit(paths=[rel], actor="admin")
    rf.set_remote(rel, state="pending")

    drop_jobs.process_queue()

    assert (archive_root / rel).exists()
    assert _job(drop_jobs, job_id)["kept"] == [{"path": rel, "reason": "not_on_server"}]


def test_restart_mid_job_restores_state_of_the_unfinished_package(archive_root, remote_on, on_server,
                                                                  drop_jobs, monkeypatch) -> None:
    first, second = on_server(2)
    calls = []
    real = drop_local._remove_local

    def crash_on_second(path):
        calls.append(path)
        if len(calls) == 2:                                      # .json schon auf remote_only, Datei noch da
            raise _Crash()
        real(path)

    monkeypatch.setattr(drop_local, "_remove_local", crash_on_second)
    job_id = drop_local.submit(paths=[first, second], actor="admin")
    with pytest.raises(_Crash):
        drop_jobs.process_queue()
    assert _meta(archive_root, second)["remote"]["state"] == "remote_only"

    drop_jobs.recover()

    assert not (archive_root / first).exists()
    assert _meta(archive_root, first)["remote"]["state"] == "remote_only"
    assert (archive_root / second).exists()
    assert _meta(archive_root, second)["remote"]["state"] == "verified"
    job = _job(drop_jobs, job_id)
    assert job["state"] == "failed" and job["error"] == "interrupted" and job["done_paths"] == [first]


def test_only_one_drop_job_at_a_time(archive_root, remote_on, on_server, drop_jobs) -> None:
    from hydrahive.archive import jobs
    a, b = on_server(2)
    drop_local.submit(paths=[a], actor="admin")
    with pytest.raises(jobs.JobConflict):
        drop_local.submit(paths=[b], actor="admin")


def test_move_started_meanwhile_stops_before_the_next_package(archive_root, remote_on, on_server, drop_jobs,
                                                               monkeypatch) -> None:
    from hydrahive.archive import location
    first, second = on_server(2)
    real = drop_local._remove_local
    moving = {"on": False}

    def remove_then_move_starts(path):
        real(path)
        moving["on"] = True

    monkeypatch.setattr(drop_local, "_remove_local", remove_then_move_starts)
    monkeypatch.setattr(location, "moving", lambda: moving["on"])
    job_id = drop_local.submit(paths=[first, second], actor="admin")
    drop_jobs.process_queue()

    assert not (archive_root / first).exists() and (archive_root / second).exists()
    job = _job(drop_jobs, job_id)
    assert job["state"] == "failed" and job["error"] == "archive_unavailable" and job["done_paths"] == [first]
