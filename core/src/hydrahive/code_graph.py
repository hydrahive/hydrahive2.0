"""Code-Graph: baut aus Projekt-Code einen lokalen Abhängigkeitsgraphen (graphify).

graphify läuft in einem isolierten, on-demand angelegten venv (nicht in den
Kern-Dependencies). Reines Code-Indexing via tree-sitter-AST — kein LLM, keine
API-Kosten, kein Datenabfluss. Output pro Projekt unter <workspace>/.graphify/out/.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.code_graph_config import get_config
from hydrahive.projects._paths import workspace_path
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


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


_METRICS_RE = re.compile(r"(\d+)\s+nodes,\s+(\d+)\s+edges,\s+(\d+)\s+communities")


def _parse_metrics(stdout: str) -> dict:
    m = _METRICS_RE.search(stdout)
    if not m:
        return {}
    return {"nodes": int(m.group(1)), "edges": int(m.group(2)), "communities": int(m.group(3))}


def build(project_id: str) -> dict:
    """Baut den Code-Graph über die konfigurierten Scan-Verzeichnisse."""
    ensure_installed()
    cfg = get_config(project_id)
    scan_dirs = cfg.get("scan_dirs", [])
    if not scan_dirs:
        raise CodeGraphError("Keine Scan-Verzeichnisse gewählt")

    root = workspace_path(project_id)
    out = _out_dir(project_id)
    out.mkdir(parents=True, exist_ok=True)

    metrics: dict = {}
    for rel in scan_dirs:
        target = (root / rel).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            continue
        if not target.is_dir():
            continue
        try:
            result = subprocess.run(
                [str(_graphify_bin()), "update", str(target)],
                check=True, capture_output=True, timeout=1800, text=True,
            )
            metrics = _parse_metrics(result.stdout) or metrics
            # graphify legt <target>/graphify-out/ an — ins gemeinsame out/ spiegeln.
            produced = target / "graphify-out"
            if produced.is_dir():
                for name in ("graph.json", "graph.html", "GRAPH_REPORT.md"):
                    src = produced / name
                    if src.is_file():
                        (out / name).write_bytes(src.read_bytes())
        except subprocess.CalledProcessError as exc:
            raise CodeGraphError(f"graphify update fehlgeschlagen: {exc.stderr[-300:] if exc.stderr else ''}") from exc
        except subprocess.TimeoutExpired as exc:
            raise CodeGraphError("graphify update Timeout") from exc

    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "scan_dirs": scan_dirs,
        "metrics": metrics,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {**meta, "report": _report_excerpt(out), **_output_paths(project_id)}


def _output_paths(project_id: str) -> dict:
    out = _out_dir(project_id)
    html = out / "graph.html"
    report = out / "GRAPH_REPORT.md"
    return {
        "html_path": str(html) if html.is_file() else None,
        "report_path": str(report) if report.is_file() else None,
    }


def _report_excerpt(out: Path) -> dict:
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
        "report": _report_excerpt(out) if meta else {},
        **_output_paths(project_id),
    }
