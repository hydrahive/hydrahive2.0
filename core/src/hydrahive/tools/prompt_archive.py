"""Agent-Tools fürs Prompt-Archiv: Prompts auflisten, lesen, speichern.

Damit kann der Agent gespeicherte Generierungs-Rezepte wiederverwenden
("mach noch ein HydraHive-Bild" → list_prompts → get_prompt → generate_image)
und gemeinsam erarbeitete Prompts ablegen (save_prompt).

ctx.user_id ist der Besitzer. Sichtbarkeit/Ownership liegt im DB-Modul.
Drei separate Tool-Objekte, alle in diesem Modul — analog datamining.py.
"""
from __future__ import annotations

from hydrahive.db import prompt_archive as db_pa
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_CATEGORIES = "image, music, system, video, speech, other"


# ---------------------------------------------------------------------------
# list_prompts — kompakte Übersicht (kein Volltext-Dump)
# ---------------------------------------------------------------------------

_LIST_DESCRIPTION = (
    "Listet gespeicherte Prompts aus dem Prompt-Archiv des Users (kompakt: "
    "id, Titel, Kategorie, Tags). Eigene + öffentliche Einträge. Optional nach "
    f"Kategorie ({_CATEGORIES}) und Volltext filtern. Für den vollen Prompt-Text "
    "danach get_prompt mit der id aufrufen."
)

_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "description": f"Optionaler Kategorie-Filter: {_CATEGORIES}.",
        },
        "query": {
            "type": "string",
            "description": "Optionaler Volltext-Filter (Titel/Prompt/Tags/Notizen).",
        },
    },
}


async def _list_execute(args: dict, ctx: ToolContext) -> ToolResult:
    items = db_pa.list_for_user(
        ctx.user_id,
        category=args.get("category") or None,
        query=args.get("query") or None,
    )
    compact = [
        {
            "id": it["id"],
            "title": it["title"],
            "category": it["category"],
            "tags": it.get("tags") or [],
            "is_public": it["is_public"],
            "use_count": it["use_count"],
        }
        for it in items
    ]
    return ToolResult.ok({"prompts": compact, "count": len(compact)})


TOOL_LIST = Tool(
    name="list_prompts",
    description=_LIST_DESCRIPTION,
    schema=_LIST_SCHEMA,
    execute=_list_execute,
    category="prompts",
)


# ---------------------------------------------------------------------------
# get_prompt — volles Rezept
# ---------------------------------------------------------------------------

_GET_DESCRIPTION = (
    "Liest einen gespeicherten Prompt als volles Rezept: prompt, style_anchor, "
    "model, params, seed, tags, notes, sample_path. Nutze style_anchor + prompt "
    "zusammen für konsistente Serien, und model/params beim Aufruf von "
    "generate_image/generate_music."
)

_GET_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "description": "ID des Prompt-Eintrags (aus list_prompts)."},
    },
    "required": ["id"],
}


async def _get_execute(args: dict, ctx: ToolContext) -> ToolResult:
    entry = db_pa.get(args.get("id") or "")
    if not entry:
        return ToolResult.fail("Kein Prompt mit dieser id gefunden")
    if entry["user_id"] != ctx.user_id and not entry["is_public"]:
        return ToolResult.fail("Dieser Prompt gehört einem anderen User und ist nicht öffentlich")
    return ToolResult.ok(entry)


TOOL_GET = Tool(
    name="get_prompt",
    description=_GET_DESCRIPTION,
    schema=_GET_SCHEMA,
    execute=_get_execute,
    category="prompts",
)


# ---------------------------------------------------------------------------
# save_prompt — neues Rezept ablegen
# ---------------------------------------------------------------------------

_SAVE_DESCRIPTION = (
    "Speichert einen Prompt als Rezept im Prompt-Archiv des Users. Nutze das "
    "wenn ihr gemeinsam einen guten Generierungs-Prompt erarbeitet habt — damit "
    "er per Klick im Chat wiederverwendbar ist. Trenne den festen Stil in "
    "style_anchor vom variablen Motiv in prompt, dann bleiben Serien konsistent."
)

_SAVE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Kurzer Anzeigename, z.B. 'HydraHive Maskottchen'."},
        "category": {"type": "string", "description": f"Kategorie: {_CATEGORIES}."},
        "prompt": {"type": "string", "description": "Der Prompt-Text (variabler Teil/Motiv)."},
        "style_anchor": {
            "type": "string",
            "description": "Fester Stil-Block der bei Serien gleich bleibt (z.B. 'oil painting, muted earth tones').",
        },
        "model": {"type": "string", "description": "Optional: Modell-ID (z.B. openai/gpt-5-image-mini)."},
        "params": {"type": "object", "description": "Optional: Generierungs-Parameter (width, height, duration, …)."},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional: Tags zum Wiederfinden."},
        "notes": {"type": "string", "description": "Optional: Freitext-Notiz (was funktioniert gut)."},
        "sample_path": {"type": "string", "description": "Optional: Pfad zu Beispiel-Medium / Referenzbild im Workspace."},
        "is_public": {"type": "boolean", "description": "Optional: für andere User sichtbar machen (default false)."},
    },
    "required": ["title", "category", "prompt"],
}


async def _save_execute(args: dict, ctx: ToolContext) -> ToolResult:
    title = (args.get("title") or "").strip()
    prompt = (args.get("prompt") or "").strip()
    if not title or not prompt:
        return ToolResult.fail("title und prompt dürfen nicht leer sein")
    entry = db_pa.create(
        ctx.user_id,
        title,
        args.get("category") or "other",
        prompt,
        style_anchor=args.get("style_anchor") or None,
        model=args.get("model") or None,
        params=args.get("params") or None,
        tags=args.get("tags") or None,
        notes=args.get("notes") or None,
        sample_path=args.get("sample_path") or None,
        is_public=bool(args.get("is_public", False)),
    )
    return ToolResult.ok({"id": entry["id"], "title": entry["title"], "saved": True})


TOOL_SAVE = Tool(
    name="save_prompt",
    description=_SAVE_DESCRIPTION,
    schema=_SAVE_SCHEMA,
    execute=_save_execute,
    category="prompts",
)
