"""Gemeinsame Hilfen für die Lösch-Tests (Spec archiv-system.md, Etappe 2). Fixture: tests/_delete_env.py."""
from __future__ import annotations

import json
import tarfile
from pathlib import Path

MODEL = "claude-sonnet-4-6"


def make_agent(name: str, *, owner: str = "testuser", agent_type: str = "specialist",
               project_id: str | None = None) -> dict:
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._paths import agent_dir, workspace_for
    from hydrahive.db.connection import init_db
    init_db()                                       # auch wenn die Testdatei allein läuft
    a = agent_config.create(agent_type=agent_type, name=name, llm_model=MODEL, tools=[], owner=owner,
                            temperature=0.7, max_tokens=1000, thinking_budget=0, project_id=project_id)
    (agent_dir(a["id"]) / "crystals.jsonl").write_text('{"k": "erinnerung"}\n')
    ws = workspace_for(a)
    ws.mkdir(parents=True, exist_ok=True)
    if agent_type != "project":
        (ws / "ergebnis.md").write_text("wichtiges Ergebnis")
    return a


def make_project(name: str, *, created_by: str = "testuser", members: list | None = None) -> dict:
    from hydrahive.db.connection import init_db
    from hydrahive.projects import config as project_config
    from hydrahive.projects._paths import workspace_path
    init_db()
    p = project_config.create(name=name, llm_model=MODEL, created_by=created_by,
                              members=members if members is not None else [created_by])
    ws = workspace_path(p["id"])
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "code.py").write_text("print('projekt')")
    return p


def make_chat(agent_id: str, *, user: str = "testuser", project_id: str | None = None, text: str = "hallo") -> str:
    from hydrahive.db import messages, sessions
    from hydrahive.db.connection import init_db
    init_db()
    s = sessions.create(agent_id=agent_id, user_id=user, project_id=project_id, title="Chat")
    messages.append(s.id, "user", text)
    messages.append(s.id, "assistant", [{"type": "text", "text": "antwort"}])
    return s.id


def only_package(root: Path, kind: str) -> Path:
    files = sorted((root / kind).glob("*.tar.gz"))
    assert len(files) == 1, files
    return files[0]


def packages(root: Path, kind: str) -> list[Path]:
    return sorted((root / kind).glob("*.tar.gz")) if (root / kind).is_dir() else []


def names(tgz: Path) -> set[str]:
    with tarfile.open(tgz) as tar:
        return set(tar.getnames())


def read_member(tgz: Path, name: str) -> str:
    with tarfile.open(tgz) as tar:
        f = tar.extractfile(name)
        assert f is not None, name
        return f.read().decode("utf-8")


def meta(tgz: Path) -> dict:
    return json.loads(tgz.with_name(tgz.name + ".json").read_text())


def session_exists(session_id: str) -> bool:
    from hydrahive.db import sessions
    return sessions.get(session_id) is not None
