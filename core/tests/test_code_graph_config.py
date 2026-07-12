import json

from hydrahive import code_graph_config, code_graph_report
from hydrahive.projects import config as project_config
from hydrahive.projects._paths import ensure_workspace


def _project_with_dirs():
    project = project_config.create(name="Graph", members=["testuser"], llm_model="test", created_by="admin")
    ws = ensure_workspace(project["id"])
    (ws / "core" / "src").mkdir(parents=True, exist_ok=True)
    (ws / "frontend" / "src").mkdir(parents=True, exist_ok=True)
    (ws / "node_modules").mkdir(parents=True, exist_ok=True)
    return project["id"], ws


def test_config_roundtrip_persists_valid_dirs():
    pid, _ = _project_with_dirs()
    result = code_graph_config.set_config(pid, ["core/src", "frontend/src"])
    assert set(result["scan_dirs"]) == {"core/src", "frontend/src"}
    fetched = code_graph_config.get_config(pid)
    assert set(fetched["scan_dirs"]) == {"core/src", "frontend/src"}
    assert fetched["updated_at"]


def test_config_rejects_traversal_and_missing():
    pid, _ = _project_with_dirs()
    result = code_graph_config.set_config(pid, ["../../../etc", "does/not/exist", "core/src"])
    # Nur das existierende, innerhalb liegende Verzeichnis überlebt.
    assert result["scan_dirs"] == ["core/src"]


def test_suggestions_find_source_dirs_and_skip_ignored():
    pid, _ = _project_with_dirs()
    suggestions = code_graph_config.suggest_scan_dirs(pid)
    assert "core/src" in suggestions or "core" in suggestions
    assert all("node_modules" not in s for s in suggestions)


def test_graph_metrics_counts_nodes_edges_communities(tmp_path):
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({
        "nodes": [{"id": "a", "community": 0}, {"id": "b", "community": 1}, {"id": "c", "community": 0}],
        "links": [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}],
    }))
    metrics = code_graph_report.graph_metrics(graph)
    assert metrics == {"nodes": 3, "edges": 2, "communities": 2}


def test_output_paths_reports_existing_files(tmp_path):
    (tmp_path / "graph.html").write_text("<html></html>")
    paths = code_graph_report.output_paths(tmp_path)
    assert paths["html_path"] and paths["report_path"] is None
