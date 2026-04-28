from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


_SUMMARY_INSTRUCTIONS = """\
Du erstellst eine strukturierte Zusammenfassung der bisherigen Konversation
in genau dem unten angegebenen Markdown-Format. Halluzinieren ist verboten —
nur Fakten aus dem Input. Schreibe knapp und konkret.

Format (genau diese Headings, in dieser Reihenfolge):

## Goal
[Was der User erreichen möchte]

## Constraints & Preferences
- [Anforderungen, Wünsche, technische Vorgaben]

## Progress
### Done
- [x] [Erledigte Aufgaben]

### In Progress
- [ ] [Aktuell laufende Arbeit]

### Blocked
- [Blocker, falls vorhanden]

## Key Decisions
- **[Entscheidung]**: [Begründung]

## Next Steps
1. [Was als nächstes gemacht werden sollte]

## Critical Context
- [Daten/Variablen/Pfade die zum Weiterarbeiten nötig sind]

<read-files>
[ein Pfad pro Zeile, gelesene Dateien]
</read-files>

<modified-files>
[ein Pfad pro Zeile, geänderte Dateien]
</modified-files>
"""


async def summarize(
    *,
    model: str,
    serialized_history: str,
    previous_summary: str | None = None,
    facts: dict | None = None,
    max_tokens: int = 4096,
) -> str:
    """Calls the LLM with the structured-summary prompt and returns markdown summary."""
    user_parts: list[str] = []
    if facts:
        user_parts.append("STRUKTURIERTE FAKTEN (gesicherte Wahrheit, übernimm wörtlich wo passend):")
        for k, v in facts.items():
            user_parts.append(f"- {k}: {v}")
        user_parts.append("")
    if previous_summary:
        user_parts.append("BISHERIGE ZUSAMMENFASSUNG (aktualisieren statt überschreiben):")
        user_parts.append(previous_summary.strip())
        user_parts.append("")
        user_parts.append("NEUE NACHRICHTEN seit dieser Zusammenfassung:")
    else:
        user_parts.append("KONVERSATION zum Zusammenfassen:")
    user_parts.append(serialized_history)

    user_content = "\n".join(user_parts)

    # Lazy import to break cycle: runner imports compaction.
    from hydrahive.runner.llm_bridge import call_with_tools
    blocks, _ = await call_with_tools(
        model=model,
        system_prompt=_SUMMARY_INSTRUCTIONS,
        messages=[{"role": "user", "content": user_content}],
        tools=[],
        temperature=0.3,
        max_tokens=max_tokens,
    )

    out_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    return "\n".join(p for p in out_parts if p).strip()
