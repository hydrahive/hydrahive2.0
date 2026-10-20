"""Ablage der Lehren je Agent (Spec 10b): `agents/<id>/lessons.jsonl` (append-only, eine Zeile je Fassung) und
`lessons_done.txt` (ausgewertete Sitzungen mit Nachrichtenzahl, „<id> <anzahl>“). Gleicher Auslöser im gleichen
Geltungsbereich → bestärken.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_KEEP = ("cue", "lesson", "part", "evidence", "quote", "confidence", "why", "key")


def _agent_dir(agent_id: str) -> Path:
    return settings.agents_dir / agent_id


def _dir(agent_id: str) -> Path:
    if not _SAFE_ID.match(agent_id or "") or agent_id in (".", ".."):
        raise ValueError("ungültige Agent-ID")
    return _agent_dir(agent_id)


@contextlib.contextmanager
def _lock(agent_id: str):
    d = _dir(agent_id)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "lessons.lock", "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield d
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rows(d: Path) -> list[dict]:
    path = d / "lessons.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("lessons: kaputte Zeile in %s übersprungen", path)
            continue
        if isinstance(row, dict) and row.get("id"):
            rows.append(row)
    return rows


def _latest(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in rows:
        out[row["id"]] = row
    return out


def current(agent_id: str) -> list[dict]:
    """Aktueller Stand: je Lehre die letzte Fassung, Reihenfolge der ersten Anlage."""
    return list(_latest(_rows(_dir(agent_id))).values())


def add(agent_id: str, lesson: dict, *, scope: str) -> dict:
    """Neue Lehre anlegen oder – gleicher Auslöser im gleichen Geltungsbereich – bestärken. Gibt die Fassung zurück."""
    sid = str(lesson.get("session_id") or "")
    with _lock(agent_id) as d:
        same = next((r for r in _latest(_rows(d)).values()
                     if r.get("key") == lesson["key"] and r.get("scope") == scope and r.get("status") == "active"), None)
        if same is not None:
            if sid in same.get("sources", []):
                return same
            row = {**same, "confirmations": int(same.get("confirmations", 0)) + 1,
                   "sources": [*same.get("sources", []), sid], "updated_at": _now()}
        else:
            row = {"id": f"les_{int(time.time() * 1000)}_{secrets.token_hex(3)}",
                   **{k: lesson.get(k, "") for k in _KEEP}, "scope": scope, "session_id": sid,
                   "created_at": _now(), "confirmations": 0, "sources": [sid], "status": "active"}
        with (d / "lessons.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row


def _update(agent_id: str, changes: dict[str, dict]) -> list[dict]:
    """Neue Fassungen bestehender Lehren anfügen (append-only, ein Schreibvorgang). changes: id → geänderte Felder."""
    with _lock(agent_id) as d:
        latest = _latest(_rows(d))
        rows = [{**latest[lid], **patch, "updated_at": _now()} for lid, patch in changes.items() if lid in latest]
        if rows:
            with (d / "lessons.jsonl").open("a", encoding="utf-8") as f:
                f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        return rows


def set_status(agent_id: str, lesson_id: str, status: str) -> dict | None:
    if status not in ("active", "contested", "retired"):
        raise ValueError("unbekannter Status")
    rows = _update(agent_id, {lesson_id: {"status": status}})
    return rows[0] if rows else None


def note_shown(agent_id: str, lessons: list[dict]) -> None:
    """L2: gezeigt zählen (Grundlage für den späteren Verfall)."""
    _update(agent_id, {r["id"]: {"shown": int(r.get("shown", 0)) + 1} for r in lessons})


def set_cue_vecs(agent_id: str, vecs: dict[str, list[float]], model: str) -> None:
    """L2: Embeddings der Auslöser ablegen, damit sie nur einmal je Modell berechnet werden."""
    _update(agent_id, {lid: {"cue_vec": [round(x, 6) for x in v], "cue_model": model} for lid, v in vecs.items()})


def _done(d: Path) -> dict[str, int]:
    path = d / "lessons_done.txt"
    out: dict[str, int] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            sid, _, count = line.partition(" ")
            if sid:
                out[sid] = int(count) if count.isdigit() else 0
    return out


def done_count(agent_id: str, session_id: str) -> int | None:
    """Nachrichtenzahl beim letzten Auswerten dieser Sitzung; None = noch nie ausgewertet."""
    return _done(_dir(agent_id)).get(session_id)


def mark_done(agent_id: str, session_id: str, count: int) -> None:
    with _lock(agent_id) as d:
        if _done(d).get(session_id) != count:
            with (d / "lessons_done.txt").open("a", encoding="utf-8") as f:
                f.write(f"{session_id} {count}\n")
