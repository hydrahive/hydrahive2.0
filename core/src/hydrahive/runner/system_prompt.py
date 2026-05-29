"""System-Prompt-Komposition für den Runner.

Entry-Point: `compose()` — eine Funktion für den gesamten System-Prompt-Bau.
Sektions-Builder als private Funktionen daneben.

Warum stable vs. volatile getrennt:
  stable  — unveränderlich pro Agent/Session: Cache-fähig (Anthropic prüft
             den gesamten System-Block byteweise, kein cache_control nötig)
  volatile — ändert sich täglich (Datum): Cache bricht nur um Mitternacht
             statt jede Minute wenn Uhrzeit enthalten wäre (Issue #141)
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def compose(
    base: str,
    *,
    extra_system: str | None,
    workspace: Path,
    summary: str | None,
    skills: list | None,
    longterm_memory: bool,
    tool_schemas: list[dict],
    allowed_tools: list[str],
    recall_cards: list[dict] | None = None,
    recall_search: list[dict] | None = None,
) -> tuple[str, str, str | None]:
    """Setzt stable-, volatile- und summary-System-Prompts zusammen.

    Side effects: wenn longterm_memory=True werden tool_schemas und
    allowed_tools um die Datamining-Tools erweitert (in-place).

    Returns: (stable_system, volatile_system, summary_system | None)
    """
    stable = _stable_section(base, extra_system=extra_system, workspace=workspace, skills=skills)
    if longterm_memory:
        stable = _inject_longterm_memory(stable, tool_schemas, allowed_tools)
    if recall_cards:
        stable += render_cards_block(recall_cards)
    volatile = _volatile_section()
    if recall_search:
        volatile += render_search_block(recall_search)
    summary_block = f"[Bisherige Zusammenfassung]\n{summary}" if summary else None
    return stable, volatile, summary_block


# ── private section builders ──────────────────────────────────────────────────

def _stable_section(
    base: str,
    *,
    extra_system: str | None,
    workspace: Path,
    skills: list | None,
) -> str:
    parts = [base]
    if extra_system:
        parts = [extra_system, base]
    stable = "\n\n".join(parts)
    stable = f"{stable}\n\nWorkspace: {workspace}"
    if skills:
        rows = "\n".join(
            f"| `{s.name}` | {s.when_to_use or s.description} |"
            for s in skills
        )
        stable += (
            "\n\n## Skills\n"
            "Lade einen Skill mit `load_skill(name)` **bevor** du mit einer Aufgabe beginnst. "
            "Wenn auch nur 1% Chance besteht dass ein Skill passt — lade ihn zuerst.\n\n"
            "| Skill | Wann nutzen |\n"
            "|-------|-------------|\n"
            f"{rows}"
        )
    return stable


def _volatile_section() -> str:
    now = datetime.now().astimezone()
    return (
        f"Datum (Server): {now.strftime('%Y-%m-%d')} ({now.strftime('%A')}). "
        "Verwende dieses Datum als Referenz, NICHT dein Trainings-Cutoff."
    )


_LONGTERM_MEMORY_HINT = (
    "\n\nLangzeitgedächtnis: für Fragen die konkret auf Vergangenes verweisen, "
    "stehen `datamining_*`-Tools zur Verfügung. Bei generischen Fragen ohne "
    "klaren Vergangenheits-Bezug direkt aus dem Kontext antworten — keine "
    "spekulativen Suchen."
)


def _inject_longterm_memory(
    stable: str,
    tool_schemas: list[dict],
    allowed_tools: list[str],
) -> str:
    """Erweitert stable-Prompt + tool_schemas + allowed_tools um Datamining-Tools."""
    from hydrahive.llm._config import load_config
    from hydrahive.tools.datamining import (
        TOOL_SEARCH, TOOL_SEMANTIC, TOOL_TIMELINE, TOOL_TODAY,
    )

    embed_model = load_config().get("embed_model", "").strip()
    available = [TOOL_SEARCH, TOOL_TODAY, TOOL_TIMELINE]
    if embed_model:
        available.append(TOOL_SEMANTIC)

    existing = {s["name"] for s in tool_schemas}
    for tool in available:
        if tool.name not in existing:
            tool_schemas.append({"name": tool.name, "description": tool.description, "input_schema": tool.schema})
        if tool.name not in allowed_tools:
            allowed_tools.append(tool.name)

    return stable + _LONGTERM_MEMORY_HINT


def render_cards_block(cards: list[dict]) -> str:
    """Recall A: kompakter, klar als *abgeleitet* gelabelter Erinnerungs-Block für
    den gecachten Stable-Prompt. Getrennt vom kuratierten Memory; leerer String
    wenn keine brauchbaren Cards."""
    lines = []
    for c in cards:
        gist = (c.get("gist") or "").strip()
        if not gist:
            continue
        topics = c.get("topics") or []
        suffix = f"  ({', '.join(str(t) for t in topics[:4])})" if topics else ""
        lines.append(f"- [{c.get('valence') or 'neutral'}] {gist}{suffix}")
    if not lines:
        return ""
    return (
        "\n\n## Erinnerungen (automatisch verdichtet — keine kuratierten Notizen)\n"
        "Essenz früherer Sessions. Bei konkretem Bedarf via `datamining_*` tiefer graben.\n"
        + "\n".join(lines)
    )


def render_search_block(cards: list[dict]) -> str:
    """Recall C: cue-getriggerte Treffer (zur aktuellen Eingabe), für den per-Turn/
    volatile Block. Trägt die session-id mit → Agent kann via `datamining_*` graben.
    Leerer String wenn keine brauchbaren Treffer."""
    lines = []
    for c in cards:
        gist = (c.get("gist") or "").strip()
        if not gist:
            continue
        src = c.get("source") if isinstance(c.get("source"), dict) else {}
        sid = (src or {}).get("session_id")
        ref = f"  [session {str(sid)[:8]}…]" if sid else ""
        lines.append(f"- {gist}{ref}")
    if not lines:
        return ""
    return (
        "\n\nRelevante frühere Erinnerungen zu deiner aktuellen Eingabe (abgeleitet):\n"
        + "\n".join(lines)
        + "\nBei Bedarf via `datamining_*` mit der session-id tiefer graben."
    )
