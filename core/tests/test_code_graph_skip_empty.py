"""Code-Graph: Verzeichnisse ohne Quellcode werden übersprungen statt den Build
abzubrechen. Befund VPS 06.10.2026, Projekt metin: client/lib (nur .pyc)
ließ den ganzen Graphen mit 400 scheitern.

graphify wird durch ein Skript ersetzt, das sich wie das echte verhält:
- Ordner mit .go-Dateien → graph.json schreiben, Exit 0
- Ordner ohne Code → "No code files found - nothing to rebuild.", Exit 1
- Ordner "kaputt" → anderer Fehler, Exit 2
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydrahive import code_graph

FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
cmd, args = sys.argv[1], sys.argv[2:]
log = pathlib.Path(os.environ["FAKE_GRAPHIFY_LOG"])
log.write_text(log.read_text() + json.dumps({"cmd": cmd, "args": args, "safe": os.environ.get("PYTHONSAFEPATH")}) + "\n") if log.exists() else log.write_text(json.dumps({"cmd": cmd, "args": args, "safe": os.environ.get("PYTHONSAFEPATH")}) + "\n")
if cmd == "update":
    d = pathlib.Path(args[0])
    if d.name == "kaputt":
        print("Traceback: echtes Problem", file=sys.stderr); sys.exit(2)
    if not any(d.rglob("*.go")):
        print("[graphify watch] No code files found - nothing to rebuild."); sys.exit(1)
    out = d / "graphify-out"; out.mkdir(exist_ok=True)
    (out / "graph.json").write_text(json.dumps({"nodes": [{"id": d.name}], "links": []}))
elif cmd == "merge-graphs":
    out = pathlib.Path(args[args.index("--out") + 1])
    nodes = [n for g in args[:args.index("--out")] for n in json.loads(pathlib.Path(g).read_text())["nodes"]]
    out.write_text(json.dumps({"nodes": nodes, "links": []}))
elif cmd == "cluster-only":
    (pathlib.Path(args[0]) / "graphify-out").mkdir(exist_ok=True)
'''


@pytest.fixture
def project(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    (ws / "server").mkdir(parents=True)
    (ws / "server" / "main.go").write_text("package main")
    (ws / "client" / "lib").mkdir(parents=True)
    (ws / "client" / "lib" / "warnings.pyc").write_bytes(b"\x03\xf3\r\n")
    (ws / "kaputt").mkdir()
    (ws / "kaputt" / "x.go").write_text("package x")

    fake = tmp_path / "graphify"
    fake.write_text(FAKE)
    fake.chmod(0o755)
    log = tmp_path / "calls.log"
    monkeypatch.setenv("FAKE_GRAPHIFY_LOG", str(log))
    monkeypatch.setattr(code_graph, "_graphify_bin", lambda: fake)
    monkeypatch.setattr(code_graph, "ensure_installed", lambda: None)
    monkeypatch.setattr(code_graph, "workspace_path", lambda pid: ws)
    monkeypatch.setattr(code_graph, "collect_output", lambda out: None)
    monkeypatch.setattr(code_graph, "report_excerpt", lambda out: {})
    monkeypatch.setattr(code_graph, "output_paths", lambda out: {})
    monkeypatch.setattr(code_graph, "graph_metrics", lambda g: {"nodes": len(json.loads(Path(g).read_text())["nodes"])})

    def use(dirs):
        monkeypatch.setattr(code_graph, "get_config", lambda pid: {"scan_dirs": dirs})
    return ws, use, log


def test_empty_dir_is_skipped_not_fatal(project):
    ws, use, _ = project
    use(["server", "client/lib"])
    res = code_graph.build("p1")
    assert res["metrics"]["nodes"] == 1
    assert res["skipped"] == [{"dir": "client/lib", "reason": "kein Quellcode gefunden"}]
    assert not (ws / "server" / "graphify-out").exists()  # aufgeräumt


def test_missing_dir_reported(project):
    _, use, _ = project
    use(["server", "gibt-es-nicht"])
    res = code_graph.build("p1")
    assert {"dir": "gibt-es-nicht", "reason": "Verzeichnis fehlt"} in res["skipped"]


def test_only_empty_dirs_still_fails_with_detail(project):
    _, use, _ = project
    use(["client/lib"])
    with pytest.raises(code_graph.CodeGraphError) as exc:
        code_graph.build("p1")
    assert "client/lib: kein Quellcode gefunden" in str(exc.value)


def test_real_error_still_aborts_and_cleans_up(project):
    ws, use, _ = project
    use(["server", "kaputt"])
    with pytest.raises(code_graph.CodeGraphError) as exc:
        code_graph.build("p1")
    assert "kaputt" in str(exc.value)
    assert not (ws / "server" / "graphify-out").exists()


def test_graphify_runs_with_safe_path(project):
    _, use, log = project
    use(["server"])
    code_graph.build("p1")
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert calls and all(c["safe"] == "1" for c in calls)


def test_status_contains_skipped(project, monkeypatch, tmp_path):
    ws, use, _ = project
    use(["server", "client/lib"])
    code_graph.build("p1")
    monkeypatch.setattr(code_graph, "bootstrap_status", lambda: {"installed": True})
    assert code_graph.status("p1")["skipped"][0]["dir"] == "client/lib"


def test_reexports_for_tools():
    from hydrahive.code_graph import CodeGraphError, _graphify_bin, ensure_installed
    from hydrahive.code_graph_install import CodeGraphError as Orig
    assert CodeGraphError is Orig
    assert callable(_graphify_bin) and callable(ensure_installed)
