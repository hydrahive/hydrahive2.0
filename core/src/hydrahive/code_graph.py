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
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.code_graph_config import get_config
from hydrahive.code_graph_install import (  # noqa: F401 — Re-Export (Tools, API)
    CodeGraphError,
    _graphify_bin,
    _venv_dir,
    bootstrap_status,
    ensure_installed,
)
from hydrahive.code_graph_report import collect_output, graph_metrics, output_paths, report_excerpt
from hydrahive.projects._paths import workspace_path

logger = logging.getLogger(__name__)

# graphify erzeugt standardmäßig KEINE interaktive graph.html über 5000 Knoten.
# Wir heben das Limit an, damit auch große Codebases eine Grafik bekommen.
VIZ_NODE_LIMIT = 20000


def _out_dir(project_id: str) -> Path:
    return workspace_path(project_id) / ".graphify" / "out"


def _run_graphify(args: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    """graphify-Aufruf mit erhöhtem Viz-Node-Limit (große Codebases → graph.html)."""
    # PYTHONSAFEPATH: Python nimmt das aktuelle Verzeichnis nicht in sys.path auf.
    # Sonst lädt graphify ggf. fremde Module aus dem Projekt (Befund 06.10.2026:
    # Python-2-warnings.pyc im Metin-Client → "bad magic number").
    env = {**os.environ, "GRAPHIFY_VIZ_NODE_LIMIT": str(VIZ_NODE_LIMIT), "PYTHONSAFEPATH": "1"}
    return subprocess.run(
        [str(_graphify_bin()), *args],
        check=True, capture_output=True, timeout=timeout, text=True, env=env,
    )


#: graphify meldet so, wenn ein Verzeichnis keinen unterstützten Quellcode hat.
_NO_CODE_MARKERS = ("No code files found", "nothing to rebuild")


class _Skipped(Exception):
    """Verzeichnis ohne verwertbaren Quellcode – überspringen, nicht abbrechen."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _extract_one(target: Path) -> Path:
    """Baut den Graphen für EIN Verzeichnis und gibt den graph.json-Pfad zurück.
    graphify schreibt nach <target>/graphify-out/ — das räumen wir danach weg.

    Ein Verzeichnis ohne Quellcode (graphify: "No code files found", Exit 1)
    wird als _Skipped gemeldet statt den ganzen Build abzubrechen (Befund VPS
    06.10.2026: client/lib mit nur .pyc ließ den Metin-Graphen scheitern)."""
    try:
        res = _run_graphify(["update", str(target)])
        text = f"{res.stdout or ''}{res.stderr or ''}"
    except subprocess.CalledProcessError as exc:
        text = f"{exc.stdout or ''}{exc.stderr or ''}"
        if not any(m in text for m in _NO_CODE_MARKERS):
            raise CodeGraphError(f"graphify update fehlgeschlagen für {target.name}: {text[-300:]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise CodeGraphError(f"graphify update Timeout für {target.name}") from exc
    produced = target / "graphify-out" / "graph.json"
    if not produced.is_file():
        raise _Skipped("kein Quellcode gefunden" if any(m in text for m in _NO_CODE_MARKERS) else "kein Graph erzeugt")
    return produced


def build(project_id: str) -> dict:
    """Baut den Code-Graph über ALLE konfigurierten Scan-Verzeichnisse und führt
    sie zu EINEM Graphen zusammen (merge-graphs), statt sie zu überschreiben."""
    cfg = get_config(project_id)
    scan_dirs = cfg.get("scan_dirs", [])
    if not scan_dirs:
        raise CodeGraphError("Keine Scan-Verzeichnisse gewählt")
    ensure_installed()

    root = workspace_path(project_id).resolve()
    out = _out_dir(project_id)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Jeden Ordner einzeln extrahieren, graph.json-Pfade sammeln.
    graphs: list[Path] = []
    scanned: list[Path] = []
    skipped: list[dict] = []
    try:
        for rel in scan_dirs:
            target = (root / rel).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                skipped.append({"dir": rel, "reason": "außerhalb des Projekts"})
                continue
            if not target.is_dir():
                skipped.append({"dir": rel, "reason": "Verzeichnis fehlt"})
                continue
            scanned.append(target)
            try:
                graphs.append(_extract_one(target))
            except _Skipped as sk:
                skipped.append({"dir": rel, "reason": sk.reason})
                logger.info("Code-Graph %s: %s übersprungen (%s)", project_id, rel, sk.reason)
    except CodeGraphError:
        _cleanup(scanned)
        raise

    if not graphs:
        _cleanup(scanned)
        detail = "; ".join(f"{s['dir']}: {s['reason']}" for s in skipped)
        raise CodeGraphError(f"Keine Quelldateien in den gewählten Verzeichnissen gefunden ({detail})")

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
        "skipped": skipped,
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
        "skipped": meta.get("skipped", []),
        "metrics": meta.get("metrics", {}),
        "report": report_excerpt(out) if meta else {},
        **output_paths(out),
    }
