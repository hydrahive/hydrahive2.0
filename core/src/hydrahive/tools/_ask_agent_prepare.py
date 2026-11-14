"""Vorprüfung und Aufbereitung für ask_agent (ausgelagert aus ask_agent.py, 14.11.2026)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def project_refusal(calling_agent_id: str, target: str) -> str | None:
    """Projekt-Agenten dürfen nur freigegebene Spezialisten beauftragen. Fehlertext oder None."""
    try:
        from hydrahive.agents import config as agent_config
        from hydrahive.projects import config as project_config
        calling = agent_config.get(calling_agent_id)
        if calling and calling.get("type") == "project":
            project_id = calling.get("project_id")
            if project_id:
                proj = project_config.get(project_id)
                allowed = proj.get("allowed_specialists", []) if proj else []
                if allowed and target not in allowed:
                    return (f"Specialist '{target}' ist für dieses Projekt nicht freigegeben. "
                            f"Freigegeben: {allowed}")
    except Exception as e:
        logger.debug("Specialists-Check übersprungen: %s", e)
    return None


def map_context(task: str, raw_context: dict) -> tuple[str, list[dict], list[str]]:
    """Komfort-Schlüssel (error_log, code_snippet, related_files) → (Auftragstext, files, errors)."""
    errors = list(raw_context.get("errors") or [])
    if raw_context.get("error_log"):
        errors.append(raw_context["error_log"])
    files = list(raw_context.get("files") or [])
    for p in raw_context.get("related_files") or []:
        files.append({"path": str(p)})
    description = task
    if raw_context.get("code_snippet"):
        description = f"{task}\n\n```\n{raw_context['code_snippet']}\n```"
    return description, files, errors


BRIEFING_REQUIRED = ("goal", "deliverable")


def missing_briefing(args: dict) -> list[str]:
    """Pflichtfelder des Briefings, die fehlen (Plan E6 T1). Abbrechen und Fortsetzen brauchen keins."""
    if args.get("cancel") or args.get("resume_token"):
        return []
    return [k for k in BRIEFING_REQUIRED if not str(args.get(k) or "").strip()]


def build_briefing(task: str, args: dict) -> str:
    """Auftrag + fester Briefing-Block für den Spezialisten (Plan E6 T2)."""
    parts = [task, f"## Ziel\n{str(args['goal']).strip()}"]
    known = str(args.get("known") or "").strip()
    if known:
        parts.append(f"## Bekannt\n{known}")
    parts.append(f"## Liefern\n{str(args['deliverable']).strip()}")
    return "\n\n".join(parts)
