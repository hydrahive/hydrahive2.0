"""Code-Graph: baut aus Projekt-Code einen lokalen Abhängigkeitsgraphen (graphify).

graphify läuft in einem isolierten, on-demand angelegten venv (nicht in den
Kern-Dependencies). Reines Code-Indexing via tree-sitter-AST — kein LLM, keine
API-Kosten, kein Datenabfluss. Output pro Projekt unter <workspace>/.graphify/out/.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.code_graph_config import get_config
from hydrahive.code_graph_report import collect_output, graph_metrics, output_paths, report_excerpt
from hydrahive.projects._paths import workspace_path
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

# graphify erzeugt standardmäßig KEINE interaktive graph.html über 5000 Knoten.
# Wir heben das Limit an, damit auch große Codebases eine Grafik bekommen.
VIZ_NODE_LIMIT = 20000


class CodeGraphError(RuntimeError):
    pass


def _venv_dir() -> Path:
    return settings.data_dir / "tools" / "graphify" / "venv"


def _graphify_bin() -> Path:
    return _venv_dir() / "bin" / "graphify"


def _out_dir(project_id: str) -> Path:
    return workspace_path(project_id) / ".graphify" / "out"


def bootstrap_status() -> dict:
    return {"installed": _graphify_bin().is_file()}


def ensure_installed() -> None:
    """Legt das isolierte venv an und installiert graphify (idempotent)."""
    if _graphify_bin().is_file():
        return
    venv = _venv_dir()
    venv.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True, timeout=120)
        subprocess.run(
            [str(venv / "bin" / "pip"), "install", "--quiet", "graphifyy"],
            check=True, capture_output=True, timeout=600,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise CodeGraphError("graphify-Installation fehlgeschlagen") from exc
    if not _graphify_bin().is_file():
        raise CodeGraphError("graphify-Binary nach Installation nicht gefunden")


def _run_graphify(args: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    """graphify-Aufruf mit erhöhtem Viz-Node-Limit (große Codebases → graph.html)."""
    env = {**os.environ, "GRAPHIFY_VIZ_NODE_LIMIT": str(VIZ_NODE_LIMIT)}
    return subprocess.run(
        [str(_graphify_bin()), *args],
        check=True, capture_output=True, timeout=timeout, text=True, env=env,
    )


def _extract_one(target: Path) -> Path | None:
    """Baut den Graphen für EIN Verzeichnis und gibt den graph.json-Pfad zurück.
    graphify schreibt nach <target>/graphify-out/ — das räumen wir danach weg."""
    try:
        _run_graphify(["update", str(target)])
    except subprocess.CalledProcessError as exc:
        raise CodeGraphError(f"graphify update fehlgeschlagen: {(exc.stderr or '')[-300:]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise CodeGraphError("graphify update Timeout") from exc
    produced = target / "graphify-out" / "graph.json"
    return produced if produced.is_file() else None


def build(project_id: str) -> dict:
    """Baut den Code-Graph über ALLE konfigurierten Scan-Verzeichnisse und führt
    sie zu EINEM Graphen zusammen (merge-graphs), statt sie zu überschreiben."""
    ensure_installed()
    cfg = get_config(project_id)
    scan_dirs = cfg.get("scan_dirs", [])
    if not scan_dirs:
        raise CodeGraphError("Keine Scan-Verzeichnisse gewählt")

    root = workspace_path(project_id).resolve()
    out = _out_dir(project_id)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Jeden Ordner einzeln extrahieren, graph.json-Pfade sammeln.
    graphs: list[Path] = []
    scanned: list[Path] = []
    for rel in scan_dirs:
        target = (root / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            continue
        if not target.is_dir():
            continue
        scanned.append(target)
        g = _extract_one(target)
        if g is not None:
            graphs.append(g)

    if not graphs:
        _cleanup(scanned)
        raise CodeGraphError("Keine Quelldateien in den gewählten Verzeichnissen gefunden")

    graph_json = out / "graph.json"
    try:
        if len(graphs) == 1:
            shutil.copy(graphs[0], graph_json)
        else:
            _run_graphify(["merge-graphs", *map(str, graphs), "--out", str(graph_json)])
        # 2. Clustering + graph.html + Report für den Gesamtgraphen erzeugen.
        _run_graphify(["cluster-only", str(out.parent), "--graph", str(graph_json)])
    except subprocess.CalledProcessError as exc:
        raise CodeGraphError(f"Graph-Zusammenführung fehlgeschlagen: {(exc.stderr or '')[-300:]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise CodeGraphError("Graph-Zusammenführung Timeout") from exc
    finally:
        _cleanup(scanned)

    # cluster-only schreibt nach <out.parent>/graphify-out/ — ins out/ ziehen.
    collect_output(out)

    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "scan_dirs": scan_dirs,
        "metrics": graph_metrics(graph_json),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {**meta, "report": report_excerpt(out), **output_paths(out)}


def _cleanup(dirs: list[Path]) -> None:
    """Entfernt die von graphify in den Scan-Ordnern angelegten graphify-out/."""
    for d in dirs:
        shutil.rmtree(d / "graphify-out", ignore_errors=True)


def status(project_id: str) -> dict:
    out = _out_dir(project_id)
    meta_path = out / "meta.json"
    meta: dict = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    return {
        **bootstrap_status(),
        "built_at": meta.get("built_at"),
        "scan_dirs": meta.get("scan_dirs", []),
        "metrics": meta.get("metrics", {}),
        "report": report_excerpt(out) if meta else {},
        **output_paths(out),
    }
