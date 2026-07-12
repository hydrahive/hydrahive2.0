import json

from hydrahive.code_graph_cycles import import_cycles


def _write_graph(tmp_path, nodes, links):
    p = tmp_path / "graph.json"
    p.write_text(json.dumps({"nodes": nodes, "links": links}))
    return p


def test_no_cycles_on_acyclic_imports(tmp_path):
    nodes = [
        {"id": "1", "source_file": "a.py"},
        {"id": "2", "source_file": "b.py"},
    ]
    links = [{"relation": "imports", "source": "1", "target": "2"}]
    assert import_cycles(_write_graph(tmp_path, nodes, links)) == []


def test_detects_real_cycle_with_full_paths(tmp_path):
    nodes = [
        {"id": "1", "source_file": "pkg/a.py"},
        {"id": "2", "source_file": "pkg/b.py"},
    ]
    links = [
        {"relation": "imports", "source": "1", "target": "2"},
        {"relation": "imports_from", "source": "2", "target": "1"},
    ]
    cycles = import_cycles(_write_graph(tmp_path, nodes, links))
    assert len(cycles) == 1
    assert "pkg/a.py" in cycles[0] and "pkg/b.py" in cycles[0]


def test_ignores_basename_collapse_across_distinct_init_files(tmp_path):
    # Zwei verschiedene __init__.py (unterschiedliche Pfade) sind KEIN Zyklus,
    # auch wenn graphify sie auf denselben Basename kollabieren würde.
    nodes = [
        {"id": "1", "source_file": "mod_a/__init__.py"},
        {"id": "2", "source_file": "mod_b/__init__.py"},
    ]
    links = [{"relation": "imports", "source": "1", "target": "2"}]
    assert import_cycles(_write_graph(tmp_path, nodes, links)) == []


def test_self_import_is_not_a_cycle(tmp_path):
    nodes = [{"id": "1", "source_file": "a.py"}]
    links = [{"relation": "imports", "source": "1", "target": "1"}]
    assert import_cycles(_write_graph(tmp_path, nodes, links)) == []


def test_non_import_relations_are_ignored(tmp_path):
    nodes = [
        {"id": "1", "source_file": "a.py"},
        {"id": "2", "source_file": "b.py"},
    ]
    links = [
        {"relation": "calls", "source": "1", "target": "2"},
        {"relation": "calls", "source": "2", "target": "1"},
    ]
    assert import_cycles(_write_graph(tmp_path, nodes, links)) == []
