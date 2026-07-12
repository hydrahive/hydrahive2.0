"""Code-Graph: Output-Konsolidierung + Report-Parsing (getrennt von der
Build-Orchestrierung in code_graph.py, damit beide Dateien fokussiert bleiben)."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


def collect_output(out: Path) -> None:
    """Zieht graph.html + Report + graph.json aus <out.parent>/graphify-out/ nach out/."""
    produced = out.parent / "graphify-out"
    if not produced.is_dir():
        return
    for name in ("graph.html", "GRAPH_REPORT.md", "graph.json"):
        src = produced / name
        if src.is_file():
            (out / name).write_bytes(src.read_bytes())
    shutil.rmtree(produced, ignore_errors=True)


def graph_metrics(graph_json: Path) -> dict:
    """Node-/Edge-/Community-Zahlen direkt aus graph.json."""
    try:
        data = json.loads(graph_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    communities = {n.get("community") for n in nodes if isinstance(n, dict) and n.get("community") is not None}
    return {"nodes": len(nodes), "edges": len(links), "communities": len(communities)}


def output_paths(out: Path) -> dict:
    html = out / "graph.html"
    report = out / "GRAPH_REPORT.md"
    return {
        "html_path": str(html) if html.is_file() else None,
        "report_path": str(report) if report.is_file() else None,
    }


def report_excerpt(out: Path) -> dict:
    """God-Nodes + Import-Zyklen aus dem Report ziehen (für die UI-Kurzsicht)."""
    report = out / "GRAPH_REPORT.md"
    if not report.is_file():
        return {}
    text = report.read_text(encoding="utf-8", errors="replace")
    god = re.findall(r"^\d+\.\s+`([^`]+)`\s+-\s+(\d+)\s+edges", text, re.MULTILINE)[:10]
    cycles = re.findall(r"cycle:\s+`([^`]+)`", text)[:10]
    return {
        "god_nodes": [{"name": n, "edges": int(e)} for n, e in god],
        "cycles": cycles,
    }
