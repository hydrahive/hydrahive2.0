from hydrahive.agents._defaults import DEFAULT_TOOLS
from hydrahive.runner._project_tool_scope import CONTAINER_ALLOWED, scope_tools
from hydrahive.tools import REGISTRY


_CONTAINER_PROJECT = {
    "id": "pdf-container",
    "mcp_server_ids": [],
    "allowed_plugins": [],
    "execution": {
        "mode": "container",
        "container": "hh-pdf-test",
        "workdir": "/work",
        "user": 1000,
    },
}


def test_read_document_ist_registriert():
    assert "read_document" in REGISTRY
    assert REGISTRY["read_document"].category == "files"


def test_master_und_projekt_bekommen_read_document_als_default():
    assert "read_document" in DEFAULT_TOOLS["master"]
    assert "read_document" in DEFAULT_TOOLS["project"]
    assert "read_document" not in DEFAULT_TOOLS["specialist"]


def test_bootstrap_ruestet_bestehende_agenten_idempotent_nach(monkeypatch):
    from hydrahive.agents import _config_utils, _paths, bootstrap

    agents = [
        {"id": "master-pdf", "name": "Master", "type": "master", "tools": ["file_read"]},
        {"id": "project-pdf", "name": "Projekt", "type": "project", "tools": ["file_read"]},
    ]
    saved = []
    monkeypatch.setattr(_config_utils, "list_all", lambda: agents)
    monkeypatch.setattr(_config_utils, "save_atomic", lambda path, value: saved.append(value.copy()))
    monkeypatch.setattr(_paths, "config_path", lambda agent_id: f"/unused/{agent_id}.json")

    bootstrap.migrate_tools()
    bootstrap.migrate_tools()

    assert all(agent["tools"].count("read_document") == 1 for agent in agents)
    assert len(saved) == 2


def test_container_bekommt_read_document_nicht():
    assert "read_document" not in CONTAINER_ALLOWED
    scoped, mcp = scope_tools(_CONTAINER_PROJECT, ["file_read", "read_document"], ["mcp"])
    assert scoped == ["file_read"]
    assert mcp == []
