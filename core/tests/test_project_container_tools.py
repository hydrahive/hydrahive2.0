"""docs/specs/projekt-container-ausfuehrung.md (K1a): Werkzeuge in Container-Projekten (Allowlist, Dispatcher)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.tools.base import ToolContext

# --- Werkzeuge in Container-Projekten ------------------------------------------------------------------------------

_CT = {"id": "p", "mcp_server_ids": [], "allowed_plugins": [],
       "execution": {"mode": "container", "container": "hh-labor-probe", "workdir": "/work", "user": 1000}}


def test_nur_die_erlaubten_werkzeuge():
    from hydrahive.runner._project_tool_scope import CONTAINER_ALLOWED, scope_tools
    tools = ["shell_exec", "file_read", "file_write", "file_patch", "todo_write", "load_skill", "web_search",
             "web_browser", "webmin_status", "webmin_call", "ask_agent", "send_mail", "generate_image",
             "datamining_search", "plugin__git-stats__git_commits", "create_specialist", "fetch_url"]
    local, mcp = scope_tools(_CT, tools, ["m1", "m2"])
    assert local == [t for t in tools if t in CONTAINER_ALLOWED]
    assert mcp == []
    for t in ("web_browser", "webmin_status", "ask_agent", "send_mail", "plugin__git-stats__git_commits"):
        assert t not in local


def test_erlaubte_liste_genau_wie_in_der_spec():
    from hydrahive.runner._project_tool_scope import CONTAINER_ALLOWED
    assert set(CONTAINER_ALLOWED) == {"shell_exec", "file_read", "file_write", "file_patch", "todo_write",
                                      "load_skill", "list_skills", "web_search", "fetch_url", "help_read",
                                      "help_search", "read_memory", "write_memory", "search_memory"}


def test_host_projekt_unveraendert():
    from hydrahive.runner._project_tool_scope import scope_tools
    tools = ["shell_exec", "web_browser", "plugin__git-stats__git_commits"]
    assert scope_tools({"id": "p", "mcp_server_ids": [], "allowed_plugins": []}, tools, ["m1"]) == (tools, ["m1"])


def test_kaputte_ausfuehrung_ergibt_keine_werkzeuge():
    from hydrahive.runner._project_tool_scope import scope_tools
    broken = {**_CT, "execution": {"mode": "container", "container": "X;y"}}
    assert scope_tools(broken, ["shell_exec", "file_read", "web_search"], ["m1"]) == ([], [])


def test_direkter_aufruf_eines_gesperrten_werkzeugs_wird_abgelehnt(client, tmp_path):
    """Auch wenn das Modell ein nicht angebotenes Werkzeug trotzdem aufruft: Der Dispatcher prüft gegen die Liste
    nach scope_tools – und die enthält für Container-Projekte nur die Allowlist."""
    from hydrahive.db import messages as messages_db
    from hydrahive.db import sessions as sessions_db
    from hydrahive.runner._project_tool_scope import scope_tools
    from hydrahive.runner.dispatcher import execute_tool
    allowed, _ = scope_tools(_CT, ["shell_exec", "web_browser", "webmin_status", "plugin__git-stats__git_commits"], [])
    s = sessions_db.create(agent_id="a1", user_id="u1", title="t")
    msg = messages_db.append(s.id, "assistant", "hi")
    ctx = ToolContext(session_id=s.id, agent_id="a1", user_id="u1", workspace=tmp_path)
    for name in ("web_browser", "webmin_status", "plugin__git-stats__git_commits"):
        res, _, _ = asyncio.run(execute_tool({"id": "x", "name": name, "input": {}}, allowed, ctx, msg.id))
        assert res.success is False and "nicht erlaubt" in (res.error or "")
