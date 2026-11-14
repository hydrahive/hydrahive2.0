"""Bestehende Agenten an Templates binden (Plan E3 T1+T2).

`propose()` schlägt je Agent ein Template vor (Regeln unten), `apply()` setzt die Zuordnung nach einer Sicherung
aller betroffenen Configs, `undo()` stellt eine Sicherung wieder her. Alte Felder bleiben in den Dateien.
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

# Reihenfolge zählt: erster Treffer gewinnt. (Muster im Namen, Template)
_SPECIALIST_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("security",), "security"),
    (("review", "auditor"), "reviewer"),
    (("test", "verifier"), "reviewer"),
    (("frontend",), "frontend"),
    (("backend", "engineer", "storage"), "backend"),
    (("übersetz", "uebersetz", "translat", "extractor", "isbn"), "klein"),
)
FALLBACK_SPECIALIST = "recherche"


def specialist_template(name: str) -> str:
    n = (name or "").lower()
    return next((tid for keys, tid in _SPECIALIST_RULES if any(k in n for k in keys)), FALLBACK_SPECIALIST)


def _backup_root() -> Path:
    return settings.data_dir / "backups" / "agent-templates"


def propose(agents: list[dict]) -> list[dict]:
    """Je Agent: bisherige Werte, vorgeschlagenes Template, ob unsicher (Regel „sonst“)."""
    from hydrahive.agents._binding import default_template_for
    out = []
    for a in sorted(agents, key=lambda x: (x.get("type") or "", (x.get("name") or "").lower())):
        if a.get("managed_by"):
            tid, unsure = "modul-schnell", False
        else:
            tid = default_template_for(a.get("type") or "specialist", a.get("name") or "")
            unsure = a.get("type") == "specialist" and tid == FALLBACK_SPECIALIST
        out.append({
            "id": a["id"], "name": a.get("name"), "type": a.get("type"), "owner": a.get("owner"),
            "managed_by": a.get("managed_by") or None, "current_template": a.get("template") or None,
            "llm_model": a.get("llm_model") or "", "fallback_models": list(a.get("fallback_models") or []),
            "max_iterations": a.get("max_iterations"), "proposed": a.get("template") or tid, "unsure": unsure,
        })
    return out


def apply(assignments: dict[str, str], *, stamp: str) -> dict:
    """{agent_id: template_id} anwenden. Erst ALLE Sicherungen, dann schreiben; bei Fehler alles zurück."""
    from hydrahive.agents._binding import check_template
    from hydrahive.agents._config_utils import get, save_atomic
    from hydrahive.agents._paths import config_path
    for tid in set(assignments.values()):
        check_template(tid)
    backup = _backup_root() / stamp
    backup.mkdir(parents=True, exist_ok=False)
    todo = []
    for aid, tid in assignments.items():
        cfg = get(aid)
        if not cfg:
            continue
        shutil.copy2(config_path(aid), backup / f"{aid}.json")
        todo.append((aid, tid, cfg))
    written: list[str] = []
    try:
        for aid, tid, cfg in todo:
            if cfg.get("template") == tid:
                continue
            save_atomic(config_path(aid), {**cfg, "template": tid})
            written.append(aid)
    except Exception:
        logger.exception("Template-Zuordnung abgebrochen – stelle %d Configs wieder her", len(written))
        for aid in written:
            shutil.copy2(backup / f"{aid}.json", config_path(aid))
        raise
    (backup / "_manifest.json").write_text(json.dumps({"assignments": assignments, "written": written}, indent=2))
    return {"backup": stamp, "written": len(written), "unchanged": len(todo) - len(written)}


def undo(stamp: str) -> int:
    from hydrahive.agents._paths import config_path, is_valid_agent_id
    backup = _backup_root() / stamp
    if not backup.is_dir() or "/" in stamp or ".." in stamp:
        raise FileNotFoundError(stamp)
    n = 0
    for f in backup.glob("*.json"):
        if f.name.startswith("_") or not is_valid_agent_id(f.stem):
            continue
        shutil.copy2(f, config_path(f.stem))
        n += 1
    return n


def backups() -> list[str]:
    root = _backup_root()
    return sorted((p.name for p in root.iterdir() if p.is_dir()), reverse=True) if root.exists() else []
