"""Spezialisten-Antwort aufteilen: Kurzfassung im Kontext, Langfassung als Datei (Spec agent-templates.md Kap. 9.4).

Vorher (`bounded_reply`) wurde auf 12.000 Zeichen gekürzt: ¾ Anfang + ¼ Ende, die Mitte fehlte – lag das Ergebnis
dort, war es weg, und die ganze lange Antwort belastete den Kontext des Auftraggebers.

Jetzt:
- Antwort ≤ Grenze → unverändert.
- Sonst: voller Text als Datei im Workspace des AUFTRAGGEBERS unter `.hydrahive/reports/<schlüssel>.md` (dort kann
  er sie mit file_read lesen; ohne bekannten Auftraggeber `$HH_DATA/agent-reports/`), im Kontext nur die Kurzfassung
  (Abschnitt „Ergebnis“/„Result“, sonst Anfang bis zum letzten Satzende vor der Grenze) plus Pfad.
- Kann die Datei nicht geschrieben werden, gilt die alte Kürzung (nie ein Fehler im Antwortweg).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_SUMMARY_CHARS = 2_000
_SAFE = re.compile(r"[^A-Za-z0-9_-]")
_RESULT = re.compile(r"^(#{1,4}\s*(Ergebnis|Result|Zusammenfassung|Summary)\b.*)$", re.IGNORECASE | re.MULTILINE)
_NEXT_HEADING = re.compile(r"^#{1,4}\s+\S", re.MULTILINE)


def _reports_dir() -> Path:
    return settings.data_dir / "agent-reports"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _summary(text: str, limit: int) -> str:
    m = _RESULT.search(text)
    if m:
        rest = text[m.end():]
        nxt = _NEXT_HEADING.search(rest)
        section = (text[m.start():m.end()] + (rest[:nxt.start()] if nxt else rest)).strip()
        if len(section) <= limit:
            return section
        text = section
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind(".\n"), cut.rfind("! "), cut.rfind("? "))
    return (cut[:end + 1] if end > limit // 3 else cut).rstrip()


def reports_dir_for_caller(caller_agentlink_id: str | None) -> Path | None:
    """Workspace des Auftraggebers aus seiner AgentLink-Kennung "<instanz>/<lokale agent_id>"."""
    if not caller_agentlink_id or "/" not in caller_agentlink_id:
        return None
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._paths import is_valid_agent_id, workspace_for
    local_id = caller_agentlink_id.rsplit("/", 1)[1]
    if not is_valid_agent_id(local_id):
        return None
    agent = agent_config.get(local_id)
    return workspace_for(agent) / ".hydrahive" / "reports" if agent else None


def split_reply(output: str, *, key: str, limit: int = DEFAULT_SUMMARY_CHARS, directory: Path | None = None) -> str:
    if len(output) <= limit:
        return output
    from hydrahive.runner._handoff_reply import bounded_reply
    safe_key = _SAFE.sub("_", key)[:80] or "antwort"
    path = (directory or _reports_dir()) / f"{safe_key}.md"
    try:
        _write(path, output)
    except OSError as exc:
        logger.warning("Langfassung %s nicht geschrieben (%s) — alte Kürzung", path, exc)
        return bounded_reply(output)
    return f"{_summary(output, limit)}\n\n… (gekürzt, {len(output)} Zeichen gesamt)\nLangfassung: {path}"


def summary_limit_for(agent: dict | None) -> int:
    """Grenze aus dem Template des Spezialisten; ohne Template die bisherige 12.000-Zeichen-Grenze."""
    from hydrahive.agents.templates import resolve
    t = resolve(agent or {})
    if t is None or t.full_report != "file":
        return 12_000
    return t.summary_max_chars
