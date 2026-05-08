from __future__ import annotations

from hydrahive.tools._memory_store import delete_key, write_key
from hydrahive.tools.base import Tool, ToolContext, ToolResult


_DESCRIPTION = (
    "Speichert eine Memory-Notiz unter dem angegebenen Schlüssel. "
    "Mit `delete=true` wird der Eintrag entfernt. "
    "Mit `expires_at` verfällt der Eintrag automatisch (+2h, +1d, +7d, +4w oder ISO-Timestamp). "
    "Beim wiederholten Schreiben auf denselben Key wird die Confidence erhöht (Reinforcement). "
    "Ähnliche Einträge werden automatisch als veraltet markiert (Contradiction Detection). "
    "Mit `project` wird der Eintrag einem Projekt zugeordnet — ohne Angabe ist er global sichtbar."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {
            "type": "string",
            "description": "Memory-Schlüssel (z.B. 'projekt.notizen').",
        },
        "content": {
            "type": "string",
            "description": "Inhalt der Notiz.",
        },
        "delete": {
            "type": "boolean",
            "description": "Eintrag löschen statt schreiben.",
            "default": False,
        },
        "expires_at": {
            "type": "string",
            "description": (
                "Ablaufzeit: relative Angabe (+2h, +1d, +7d, +4w) oder ISO-Timestamp."
            ),
        },
        "confidence": {
            "type": "number",
            "description": (
                "Initiale Verlässlichkeit (0.0–1.0, default 0.5). "
                "Nur für neue Einträge relevant."
            ),
        },
        "project": {
            "type": "string",
            "description": (
                "Projekt-Kontext für diesen Eintrag. "
                "Ohne Angabe: global (in allen Projekten sichtbar). "
                "Beispiel: 'hydrahive2', 'minecraft-server'."
            ),
        },
    },
    "required": ["key"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    key = (args.get("key") or "").strip()
    if not key:
        return ToolResult.fail("Leerer key")

    if args.get("delete"):
        existed = delete_key(ctx.agent_id, key)
        if not existed:
            return ToolResult.fail(f"Memory-Eintrag '{key}' existiert nicht")
        return ToolResult.ok(f"Memory '{key}' gelöscht")

    content = args.get("content")
    if content is None:
        return ToolResult.fail("content fehlt")
    if not isinstance(content, str):
        return ToolResult.fail("content muss ein String sein")

    confidence = args.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            return ToolResult.fail("confidence muss eine Zahl zwischen 0.0 und 1.0 sein")
        if not (0.0 <= confidence <= 1.0):
            return ToolResult.fail("confidence muss zwischen 0.0 und 1.0 liegen")

    # project: explizit übergeben > aktives Projekt aus Kontext > None (global)
    project = args.get("project") or None

    expires_at = args.get("expires_at")
    entry, superseded = write_key(
        ctx.agent_id, key, content,
        expires_at=expires_at or None,
        confidence=confidence,
        project=project,
    )

    extra: dict = {
        "confidence": entry["confidence"],
        "reinforcements": entry["reinforcements"],
    }
    if entry.get("project"):
        extra["project"] = entry["project"]
    if entry.get("expires_at"):
        extra["expires_at"] = entry["expires_at"]
    if superseded:
        extra["superseded"] = superseded
        extra["warning"] = (
            f"{len(superseded)} potenziell widersprüchliche(r) Eintrag/Einträge "
            f"als veraltet markiert: {', '.join(superseded)}"
        )

    return ToolResult.ok(
        f"Memory '{key}' gespeichert",
        key=key,
        bytes=len(content.encode("utf-8")),
        **extra,
    )


TOOL = Tool(name="write_memory", description=_DESCRIPTION, schema=_SCHEMA, execute=_execute, category="memory")
