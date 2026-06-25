"""DB-Operationen für das Prompt-Archiv (Prompt Library).

Speichert Generierungs-Prompts als volles "Rezept" pro User: Prompt-Text,
Style-Anchor, Modell, Parameter, Tags, Beispiel-Medium, Sichtbarkeit.

Sichtbarkeitsregel: Ein User sieht eigene Einträge (alle) + fremde mit
is_public=1. Schreiben/Löschen nur am eigenen Eintrag (Ownership in der API
geprüft — diese Schicht ist reines Datenzugriffs-CRUD).

JSON-Felder (params, tags) werden hier transparent serialisiert/deserialisiert,
damit Aufrufer mit echten dicts/lists arbeiten statt mit Strings.
"""
from __future__ import annotations

import json
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

CATEGORIES = ("image", "music", "system", "video", "speech", "other")


def _row(r: Any) -> dict:
    """SQLite-Row → dict, mit JSON-Feldern als echte Python-Objekte."""
    d = dict(r)
    d["params"] = _loads(d.get("params"), {})
    d["tags"] = _loads(d.get("tags"), [])
    d["is_public"] = bool(d.get("is_public"))
    return d


def _loads(raw: Any, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


def _dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Create / Read
# ---------------------------------------------------------------------------

def create(
    user_id: str,
    title: str,
    category: str,
    prompt: str,
    *,
    style_anchor: str | None = None,
    model: str | None = None,
    params: dict | None = None,
    seed: int | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
    sample_path: str | None = None,
    is_public: bool = False,
) -> dict:
    """Legt einen neuen Prompt-Eintrag an und gibt ihn zurück."""
    pid = uuid7()
    cat = category if category in CATEGORIES else "other"
    with db() as conn:
        conn.execute(
            """
            INSERT INTO prompt_archive
                (id, user_id, title, category, prompt, style_anchor, model,
                 params, seed, tags, notes, sample_path, is_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pid, user_id, title, cat, prompt, style_anchor, model,
                _dumps(params), seed, _dumps(tags), notes, sample_path,
                1 if is_public else 0,
            ),
        )
    return get(pid)  # type: ignore[return-value]


def get(prompt_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM prompt_archive WHERE id = ?", (prompt_id,)
        ).fetchone()
    return _row(row) if row else None


def list_for_user(
    user_id: str,
    *,
    category: str | None = None,
    query: str | None = None,
    include_public: bool = True,
) -> list[dict]:
    """Eigene Einträge + (optional) fremde öffentliche.

    Filter: category exakt, query als Volltext (LIKE auf title/prompt/tags/notes).
    Sortierung: meistgenutzt zuerst, dann zuletzt geändert.
    """
    where = ["(user_id = ?" + (" OR is_public = 1)" if include_public else ")")]
    args: list[Any] = [user_id]
    if category and category in CATEGORIES:
        where.append("category = ?")
        args.append(category)
    if query:
        where.append("(title LIKE ? OR prompt LIKE ? OR tags LIKE ? OR notes LIKE ?)")
        like = f"%{query}%"
        args.extend([like, like, like, like])
    sql = (
        "SELECT * FROM prompt_archive WHERE "
        + " AND ".join(where)
        + " ORDER BY use_count DESC, updated_at DESC"
    )
    with db() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [_row(r) for r in rows]


# ---------------------------------------------------------------------------
# Update / Delete
# ---------------------------------------------------------------------------

_UPDATABLE = {
    "title", "category", "prompt", "style_anchor", "model",
    "params", "seed", "tags", "notes", "sample_path", "is_public",
}


def update(prompt_id: str, user_id: str, **fields: Any) -> dict | None:
    """Aktualisiert nur erlaubte Felder am EIGENEN Eintrag.

    Gibt den aktualisierten Eintrag zurück, oder None wenn der Eintrag nicht
    existiert oder dem User nicht gehört (kein Update durchgeführt).
    """
    existing = get(prompt_id)
    if not existing or existing["user_id"] != user_id:
        return None
    sets: list[str] = []
    args: list[Any] = []
    for key, val in fields.items():
        if key not in _UPDATABLE:
            continue
        if key in ("params", "tags"):
            val = _dumps(val)
        elif key == "is_public":
            val = 1 if val else 0
        elif key == "category" and val not in CATEGORIES:
            val = "other"
        sets.append(f"{key} = ?")
        args.append(val)
    if not sets:
        return existing
    sets.append("updated_at = ?")
    args.append(now_iso())
    args.extend([prompt_id, user_id])
    with db() as conn:
        conn.execute(
            f"UPDATE prompt_archive SET {', '.join(sets)} WHERE id = ? AND user_id = ?",
            args,
        )
    return get(prompt_id)


def delete(prompt_id: str, user_id: str) -> bool:
    """Löscht einen eigenen Eintrag. True wenn etwas gelöscht wurde."""
    with db() as conn:
        cur = conn.execute(
            "DELETE FROM prompt_archive WHERE id = ? AND user_id = ?",
            (prompt_id, user_id),
        )
    return cur.rowcount > 0


def bump_use_count(prompt_id: str) -> None:
    """Erhöht use_count um 1 (wird beim Laden in den Chat aufgerufen)."""
    with db() as conn:
        conn.execute(
            "UPDATE prompt_archive SET use_count = use_count + 1 WHERE id = ?",
            (prompt_id,),
        )
