"""Beschreibung und JSON-Schema des Werkzeugs ask_agent (ausgelagert aus ask_agent.py, 14.11.2026)."""
from __future__ import annotations

from hydrahive.tools import _ask_agent_background as _bg

DESCRIPTION = (
    "Beauftragt einen anderen Agenten über AgentLink. "
    "Verwende für Handoffs an Spezialisten oder Project-Agents. "
    "Erreichbar sind nur eigene Agenten (Admins: alle). "
    + _bg.DESCRIPTION_HINT
)

SCHEMA = {
    "type": "object",
    "properties": {
        "agent_id": {
            "type": "string",
            "description": (
                "ID oder Name des Ziel-Agenten. "
                "Für Federation-Workstations: 'persona@workstation-name', z.B. 'geralt@projektx-till'."
            ),
        },
        "task": {"type": "string", "description": "Aufgabenbeschreibung für den Ziel-Agenten."},
        "task_type": {
            "type": "string",
            "description": "Task-Typ. Default 'feature'.",
            "enum": ["bug_fix", "feature", "review", "research", "refactor"],
        },
        "context": {
            "type": "object",
            "description": (
                "Optionale Zusatz-Daten für den Ziel-Agenten. Unterstützte Keys: "
                "error_log (str), code_snippet (str), related_files (list[str]), "
                "files (list[dict]), errors (list[str]), git (dict)."
            ),
            "properties": {
                "error_log":      {"type": "string"},
                "code_snippet":   {"type": "string"},
                "related_files":  {"type": "array", "items": {"type": "string"}},
                "files":          {"type": "array",  "items": {"type": "object"}},
                "errors":         {"type": "array",  "items": {"type": "string"}},
                "git":            {"type": "object"},
            },
        },
        "profile": {
            "type": "string",
            "enum": ["quick", "standard", "deep"],
            "description": ("Nur für Spezialisten OHNE Agenten-Template (Altbestand). Mit Template gilt dessen "
                            "Budget; mehr gibt es nur über overrun."),
        },
        "overrun": {
            "type": "boolean",
            "description": ("Budget des Ziel-Templates überschreiten (höchstens um die dort erlaubten Prozent). "
                            "Nur mit overrun_reason."),
        },
        "overrun_reason": {
            "type": "string", "minLength": 10, "maxLength": 500,
            "description": "Pflicht bei overrun: warum der Auftrag mehr Budget braucht.",
        },
        "resume_token": {
            "type": "string",
            "pattern": "^[A-Za-z0-9_-]{8,128}$",
            "description": "Einmal-Token aus einem pausierten Spezialistenlauf.",
        },
        "required_skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optionale Skill-Liste die der Ziel-Agent haben muss.",
        },
        "wait": _bg.WAIT_SCHEMA,
        "cancel": _bg.CANCEL_SCHEMA,
    },
    # agent_id/task sind nur fürs Beauftragen nötig (Prüfung in _execute);
    # für cancel= nicht. Darum hier nicht als Pflichtfelder markiert.
    "required": [],
}
