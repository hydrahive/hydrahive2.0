import asyncio

from hydrahive.tools import REGISTRY
from hydrahive.tools.base import ToolContext
from hydrahive.tools import code_graph_tools as cgt
from hydrahive.projects._paths import ensure_workspace
from hydrahive.projects import config as project_config


def test_graph_tools_registered():
    for name in ("graph_query", "graph_explain", "graph_path", "graph_affected"):
        assert name in REGISTRY
        assert REGISTRY[name].category == "code"


def _ctx(project_id):
    ws = ensure_workspace(project_id)
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=ws, project_id=project_id)


def test_query_without_graph_returns_hint():
    project = project_config.create(name="NoGraph", members=["testuser"], llm_model="test", created_by="admin")
    ctx = _ctx(project["id"])
    result = asyncio.run(cgt._query({"question": "was hängt an X"}, ctx))
    assert not result.success
    assert "Code-Graph" in (result.error or "")


def test_query_missing_question():
    project = project_config.create(name="NoQ", members=["testuser"], llm_model="test", created_by="admin")
    ctx = _ctx(project["id"])
    result = asyncio.run(cgt._query({}, ctx))
    assert not result.success
    assert "question" in (result.error or "")
