"""Agent löschen: ins Archiv oder unwiderruflich (Spec archiv-system.md, Etappe 2).

Reihenfolge: sperren → messen → Platz → packen → prüfen → löschen.
Geht vor dem Löschen etwas schief, bleibt alles, wie es war.
"""
from __future__ import annotations

import json

import pytest

from hydrahive.archive import deletion, package
from tests._delete_fixtures import (
    make_agent, make_chat, meta, names, only_package, packages, read_member, session_exists,
)

pytest_plugins = ["tests._delete_fixtures"]  # Fixture `archive_root`


def _agent_exists(agent_id: str) -> bool:
    from hydrahive.agents import config as agent_config
    return agent_config.get(agent_id) is not None


def _workspace(agent: dict):
    from hydrahive.agents._paths import workspace_for
    return workspace_for(agent)


def test_archive_packs_everything_then_deletes(archive_root) -> None:
    a = make_agent("Archiv-Agent A")
    sid = make_chat(a["id"], text="merk dir das")

    result = deletion.run("agent", a["id"], "archive", actor="admin")

    assert result["state"] == "done", result
    tgz = only_package(archive_root, "agents")
    content = names(tgz)
    assert "agent/config.json" in content and "agent/crystals.jsonl" in content
    assert "workspace/ergebnis.md" in content
    chat = json.loads(read_member(tgz, f"sessions/{sid}.json"))
    assert chat["session"]["id"] == sid
    assert any(m["content"] == "merk dir das" for m in chat["messages"])
    info = meta(tgz)
    assert info["kind"] == "agents" and info["reason"] == "agent_deleted" and info["source_id"] == a["id"]
    assert info["entries"] == len(content)
    assert not _agent_exists(a["id"]) and not _workspace(a).exists()
    assert not session_exists(sid)


def test_permanent_deletes_everything_without_package(archive_root) -> None:
    a = make_agent("Weg-Agent B")
    sid = make_chat(a["id"])

    result = deletion.run("agent", a["id"], "permanent", actor="admin")

    assert result["state"] == "done", result
    assert packages(archive_root, "agents") == []
    assert not _agent_exists(a["id"]) and not _workspace(a).exists()
    assert not session_exists(sid)


def test_agent_is_disabled_while_packing(archive_root, monkeypatch) -> None:
    from hydrahive.agents import config as agent_config
    a = make_agent("Gesperrt C")
    seen = []
    real = package.pack

    def spy(**kw):
        seen.append(agent_config.get(a["id"])["status"])
        return real(**kw)

    monkeypatch.setattr(package, "pack", spy)
    deletion.run("agent", a["id"], "archive", actor="admin")

    assert seen == ["disabled"]


def test_running_chat_is_stopped(archive_root, monkeypatch) -> None:
    from hydrahive.archive import _lock
    a = make_agent("Laeuft D")
    sid = make_chat(a["id"])
    stopped = []
    monkeypatch.setattr(_lock, "stop_run", lambda session_id: stopped.append(session_id))

    deletion.run("agent", a["id"], "permanent", actor="admin")

    assert stopped == [sid]


@pytest.mark.parametrize("status", ["active", "disabled"])
def test_failed_packing_deletes_nothing(archive_root, monkeypatch, status) -> None:
    from hydrahive.agents import config as agent_config
    a = make_agent(f"Bleibt E {status}")
    agent_config.update(a["id"], status=status)
    sid = make_chat(a["id"])

    def boom(**kw):
        raise OSError("Platte voll")

    monkeypatch.setattr(package, "pack", boom)
    result = deletion.run("agent", a["id"], "archive", actor="admin")

    assert result["state"] == "failed" and result["error"] == "pack_failed"
    assert agent_config.get(a["id"])["status"] == status
    assert (_workspace(a) / "ergebnis.md").exists() and session_exists(sid)
    assert packages(archive_root, "agents") == []


def test_broken_package_deletes_nothing(archive_root, monkeypatch) -> None:
    a = make_agent("Kaputt F")
    real = package.pack

    def tamper(**kw):
        entry = real(**kw)
        path = archive_root / "agents" / entry["file"]
        path.write_bytes(path.read_bytes()[:-10] + b"0123456789")
        return entry

    monkeypatch.setattr(package, "pack", tamper)
    result = deletion.run("agent", a["id"], "archive", actor="admin")

    assert result["state"] == "failed" and result["error"] == "verify_failed"
    assert _agent_exists(a["id"]) and (_workspace(a) / "ergebnis.md").exists()
    assert packages(archive_root, "agents") == []


def test_not_enough_space_deletes_nothing(archive_root, monkeypatch) -> None:
    a = make_agent("Voll G")
    monkeypatch.setattr(deletion, "free_bytes", lambda path: 10)

    result = deletion.run("agent", a["id"], "archive", actor="admin")

    assert result["state"] == "failed" and result["error"] == "not_enough_space"
    assert _agent_exists(a["id"])


def test_archive_moving_blocks_archive_but_not_permanent(archive_root, monkeypatch) -> None:
    from hydrahive.archive import location
    a, b = make_agent("Umzug H"), make_agent("Umzug I")
    monkeypatch.setattr(location, "moving", lambda: True)

    blocked = deletion.run("agent", a["id"], "archive", actor="admin")
    gone = deletion.run("agent", b["id"], "permanent", actor="admin")

    assert blocked["state"] == "failed" and blocked["error"] == "archive_unavailable"
    assert _agent_exists(a["id"])
    assert gone["state"] == "done" and not _agent_exists(b["id"])


def test_agent_secrets_are_masked_in_package(archive_root) -> None:
    from hydrahive.agents import config as agent_config
    a = make_agent("Postfach J")
    agent_config.update(a["id"], tool_config={"smtp": {"host": "mail", "user": "u", "password": "SehrGeheim123"}})

    deletion.run("agent", a["id"], "archive", actor="admin")

    cfg = read_member(only_package(archive_root, "agents"), "agent/config.json")
    assert "SehrGeheim123" not in cfg and json.loads(cfg)["tool_config"]["smtp"]["password"] == "***"


def test_project_agent_keeps_project_workspace(archive_root) -> None:
    """Der Projekt-Agent teilt sich den Arbeitsordner mit dem Projekt – der bleibt."""
    from tests._delete_fixtures import make_project
    p = make_project("Mit Agent K")
    from hydrahive.projects._paths import workspace_path

    deletion.run("agent", p["agent_id"], "permanent", actor="admin")

    assert not _agent_exists(p["agent_id"])
    assert (workspace_path(p["id"]) / "code.py").exists()


def test_unknown_agent(archive_root) -> None:
    result = deletion.run("agent", "gibt-es-nicht", "permanent", actor="admin")
    assert result["state"] == "failed" and result["error"] == "not_found"
