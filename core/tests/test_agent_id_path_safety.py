"""Agent-IDs dürfen keine Pfade sein (Sicherheitsprüfung 01.10.2026).

agent_config.get(agent_id) baute ``agents_dir / agent_id / "config.json"``
ohne Prüfung. Mit ``agent_id="../workspaces/projects/<P>/forge"`` las HydraHive
eine selbst geschriebene config.json aus einem Projekt-Workspace: eigener
``owner`` (Zugriffsprüfung bestanden), fremde ``id`` (System-Prompt,
Workspace, Projekt). Erreichbar u. a. über POST /api/sessions — 201.
"""
from __future__ import annotations

import json

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.agents import _paths
from hydrahive.settings import settings

BAD_IDS = [
    "../workspaces/projects/P-forge/forge",
    "..",
    "a/../b",
    "/etc",
    "x\\..\\y",
    "agent/sub",
    "",
    " test-agent-001",
    "a" * 129,
    "%2e%2e",
]


@pytest.fixture
def forged(setup_test_env):
    evil = settings.data_dir / "workspaces" / "projects" / "P-forge" / "forge"
    evil.mkdir(parents=True, exist_ok=True)
    (evil / "config.json").write_text(json.dumps({
        "id": "test-agent-001", "name": "gefälscht", "type": "specialist",
        "owner": "testuser", "llm_model": "claude-haiku-4-5",
    }))
    return evil


@pytest.mark.parametrize("bad", BAD_IDS)
def test_get_rejects_path_like_ids(forged, bad):
    assert agent_config.get(bad) is None


@pytest.mark.parametrize("bad", BAD_IDS)
def test_paths_never_leave_agents_dir(bad):
    for fn in (_paths.config_path, _paths.system_prompt_path, _paths.agent_dir, _paths.soul_dir):
        with pytest.raises(ValueError):
            fn(bad)


def test_config_id_must_match_folder(setup_test_env):
    d = settings.agents_dir / "ordner-a"
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text(json.dumps({
        "id": "andere-id", "name": "x", "type": "specialist", "owner": "testuser",
        "llm_model": "claude-haiku-4-5",
    }))
    assert agent_config.get("ordner-a") is None


def test_normal_agent_still_loads(setup_test_env):
    assert agent_config.get("test-agent-001")["id"] == "test-agent-001"


def test_session_api_rejects_traversal_agent(client, auth_headers, forged):
    r = client.post("/api/sessions", headers=auth_headers,
                    json={"agent_id": "../workspaces/projects/P-forge/forge"})
    assert r.status_code == 404
