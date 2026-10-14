"""Lösch-Aufträge: Reihe, Neustart vor und nach dem Löschen, externe Instanz (Spec archiv-system.md, Etappe 2)."""
from __future__ import annotations

import pytest

from hydrahive.archive import deletion, package
from tests._delete_fixtures import make_agent, make_chat, names, only_package, packages, session_exists

pytest_plugins = ["tests._delete_env"]  # Fixture `archive_root`


class _Crash(BaseException):
    """Stellt einen Absturz/Neustart nach: wird von keinem `except Exception` gefangen."""


@pytest.fixture
def jobs(monkeypatch):
    from hydrahive.archive import jobs as j
    monkeypatch.setattr(j, "_start_worker", lambda: None)
    j.reset_for_tests()
    yield j
    j.reset_for_tests()


def test_queue_runs_in_order(archive_root, jobs) -> None:
    from hydrahive.agents import config as agent_config
    a, b = make_agent("Reihe A"), make_agent("Reihe B")
    first = jobs.submit("agent", a["id"], "permanent", actor="admin")
    second = jobs.submit("agent", b["id"], "archive", actor="admin")

    assert [j["id"] for j in jobs.list_jobs()["queued"]] == [first, second]
    jobs.process_queue()

    done = jobs.list_jobs()["done"]
    assert [j["id"] for j in done[:2]] == [second, first]       # neueste zuerst
    assert all(j["state"] == "done" for j in done[:2])
    assert agent_config.get(a["id"]) is None and agent_config.get(b["id"]) is None


def test_crash_before_delete_rolls_back(archive_root, jobs, monkeypatch) -> None:
    from hydrahive.agents import config as agent_config
    a = make_agent("Absturz A")
    sid = make_chat(a["id"])

    def crash(**kw):
        raise _Crash()

    monkeypatch.setattr(package, "pack", crash)
    job_id = jobs.submit("agent", a["id"], "archive", actor="admin")
    with pytest.raises(_Crash):
        jobs.process_queue()
    assert agent_config.get(a["id"])["status"] == "disabled"       # mitten im Auftrag

    jobs.recover()

    assert agent_config.get(a["id"])["status"] == "active" and session_exists(sid)
    assert packages(archive_root, "agents") == []
    [job] = jobs.list_jobs()["done"]
    assert job["id"] == job_id and job["state"] == "failed" and job["error"] == "interrupted"


def test_crash_while_deleting_finishes_after_restart(archive_root, jobs, monkeypatch) -> None:
    from hydrahive.agents import config as agent_config
    a = make_agent("Absturz B")
    sid = make_chat(a["id"])
    real = agent_config.delete
    calls = {"n": 0}

    def crash_once(agent_id):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _Crash()
        return real(agent_id)

    monkeypatch.setattr(agent_config, "delete", crash_once)
    jobs.submit("agent", a["id"], "archive", actor="admin")
    with pytest.raises(_Crash):
        jobs.process_queue()

    jobs.recover()

    assert agent_config.get(a["id"]) is None and not session_exists(sid)
    assert "agent/config.json" in names(only_package(archive_root, "agents"))
    [job] = jobs.list_jobs()["done"]
    assert job["state"] == "done"


def test_hard_kill_while_packing_leaves_no_half_packages(archive_root, jobs, monkeypatch) -> None:
    """Harter Neustart (SIGKILL) mitten im Packen: Weder das halbe Paket (.part) noch ein schon fertiges
    Teilpaket bleiben liegen. Gefunden im frischen Container: 800 MB .part nach Neustart."""
    import uuid

    from hydrahive.api.middleware import users
    from tests._delete_fixtures import make_project
    name = f"kill{uuid.uuid4().hex[:6]}"
    users.create(name, "testpass123", role="user")
    make_project("Kill-Projekt", created_by=name, members=[name])
    snapshot: dict = {}

    def kill_mid_user_package(size: int) -> None:
        parts = list((archive_root / "users").glob("*.part")) if (archive_root / "users").is_dir() else []
        if packages(archive_root, "projects") and parts and not snapshot:
            for f in archive_root.rglob("*"):          # so liegt es da, wenn der Prozess hart stirbt
                if f.is_file():
                    snapshot[f] = f.read_bytes()
            raise _Crash()

    real_pack = package.pack
    monkeypatch.setattr(package, "pack", lambda **kw: real_pack(**{**kw, "on_file": lambda n: (
        kw["on_file"](n), kill_mid_user_package(n))}))
    jobs.submit("user", name, "archive", actor="admin")
    with pytest.raises(_Crash):
        jobs.process_queue()
    for f, data in snapshot.items():                    # SIGKILL räumt nichts auf
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
    assert any(f.name.endswith(".part") for f in snapshot) and packages(archive_root, "projects")

    jobs.recover()

    left = sorted(str(f.relative_to(archive_root)) for f in archive_root.rglob("*") if f.is_file()
                  and not f.relative_to(archive_root).parts[0].startswith("."))
    assert left == [], left
    assert users.get_by_username(name) is not None
    [job] = [j for j in jobs.list_jobs()["done"] if j["target"] == name]
    assert job["state"] == "failed" and job["error"] == "interrupted"


def test_waiting_jobs_survive_restart(archive_root, jobs) -> None:
    """Bestätigt ist bestätigt: Ein wartender Auftrag (noch nichts angefasst) läuft nach dem Neustart weiter."""
    from hydrahive.agents import config as agent_config
    a = make_agent("Wartet C")
    job_id = jobs.submit("agent", a["id"], "permanent", actor="admin")

    jobs.recover()
    assert [j["id"] for j in jobs.list_jobs()["queued"]] == [job_id]
    jobs.process_queue()

    assert agent_config.get(a["id"]) is None


def test_progress_is_reported(archive_root) -> None:
    a = make_agent("Fortschritt D")
    result = deletion.run("agent", a["id"], "archive", actor="admin")
    assert result["bytes_total"] > 0 and result["files_total"] >= 3
    assert result["package"].endswith(".tar.gz")


def test_external_instance_goes_with_its_user(archive_root) -> None:
    from hydrahive.agents import external_instances as ei
    from hydrahive.api.middleware import api_keys, users
    inst = ei.create_instance("extern-x", "claude-sonnet-4-6")

    result = deletion.run("instance", inst["agent_id"], "archive", actor="admin")

    assert result["state"] == "done", result
    content = names(only_package(archive_root, "agents"))
    assert "agent/config.json" in content and "user/user.json" in content
    assert users.get_by_username("extern-x") is None and api_keys.list_keys(username="extern-x") == []
