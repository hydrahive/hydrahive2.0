"""Arbeitsdateien fürs Paket: Chats als JSON, Konfigs mit *** statt Geheimnis, Nutzer-Zeilen als jsonl.

Alles landet in `archive/.arbeit/<auftrag>/` – dieselbe Platte wie das Archiv, der Katalog zeigt es
nicht (Punkt-Ordner) und es wird nach dem Auftrag entfernt (Spec archiv-system.md, Etappe 2).
"""
from __future__ import annotations

import dataclasses
import json
import shutil
from pathlib import Path
from typing import Any

from hydrahive.archive._paths import archive_root

MASK = "***"
WORK_DIR = ".arbeit"

# Persönliche Kern-Tabellen und die Spalte, die den Nutzer nennt (Spec, Fund 13.10.).
# „name“ = Nutzername, „id“ = unveränderliche Nutzer-ID.
USER_TABLES: tuple[tuple[str, str, str], ...] = (
    ("user_preferences", "user_id", "name"), ("prompt_archive", "user_id", "name"),
    ("streaming_credentials", "user_id", "name"), ("streaming_jobs", "user_id", "name"),
    ("teamchat_identities", "user_id", "name"), ("vault_pins", "user_id", "id"),
    ("health_ingest", "user_id", "name"), ("health_daily", "user_id", "name"),
    ("fhir_resources", "user_id", "name"), ("ega_records", "user_id", "name"),
    ("scheduled_agent_tasks", "owner", "name"),
)


def work_dir(job_id: str) -> Path:
    d = archive_root() / WORK_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def drop_work_dir(job_id: str) -> None:
    shutil.rmtree(archive_root() / WORK_DIR / job_id, ignore_errors=True)


def _write(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def write_sessions(folder: Path, session_ids: list[str]) -> list[tuple[str, Path]]:
    """Je Chat eine Datei `sessions/<id>.json` mit Kopf und allen Nachrichten (inkl. Werkzeugaufrufen)."""
    from hydrahive.db import messages, sessions
    if not session_ids:
        return []
    out = folder / "sessions"
    for sid in session_ids:
        s = sessions.get(sid)
        if s is None:
            continue
        msgs = [dataclasses.asdict(m) for m in messages.list_for_session(sid)]
        _write(out / f"{sid}.json", {"session": dataclasses.asdict(s), "messages": msgs})
    return [("sessions", out)]


def masked_agent_config(folder: Path, agent: dict) -> Path:
    """Agent-Konfig mit *** statt Postfach-Passwort (smtp/imap)."""
    cfg = json.loads(json.dumps(agent))
    for block in ("smtp", "imap"):
        b = (cfg.get("tool_config") or {}).get(block)
        if isinstance(b, dict) and b.get("password"):
            b["password"] = MASK
    return _write(folder / "config.json", cfg)


def masked_project_config(folder: Path, project: dict) -> Path:
    """Projekt-Konfig mit *** statt webhook_secret und git_token (Entscheidung 2)."""
    cfg = json.loads(json.dumps(project))
    if cfg.get("webhook_secret"):
        cfg["webhook_secret"] = MASK
    if cfg.get("git_token"):
        cfg["git_token"] = MASK
    for repo in (cfg.get("git_repos") or {}).values():
        if isinstance(repo, dict) and repo.get("git_token"):
            repo["git_token"] = MASK
    return _write(folder / "config.json", cfg)


def masked_discord(folder: Path, path: Path) -> Path | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and data.get("bot_token"):
        data["bot_token"] = MASK
    return _write(folder / "discord.json", data)


def user_record(folder: Path, username: str) -> Path:
    """Nutzer-Eintrag ohne Passwort-Hash."""
    from hydrahive.api.middleware import users
    return _write(folder / "user.json", users.get_by_username(username) or {"username": username})


def user_rows(folder: Path, username: str, user_id: str) -> Path | None:
    """`db/<tabelle>.jsonl` je persönlicher Kern-Tabelle. Verschlüsselte Spalten bleiben, wie sie sind."""
    from hydrahive.db.connection import db
    out = folder / "db"
    wrote = False
    with db() as conn:
        for table, column, key in USER_TABLES:
            if not _table_exists(conn, table):
                continue
            value = username if key == "name" else user_id
            rows = conn.execute(f"SELECT * FROM {table} WHERE {column} = ?", (value,)).fetchall()
            if not rows:
                continue
            out.mkdir(parents=True, exist_ok=True)
            with open(out / f"{table}.jsonl", "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(dict(r), ensure_ascii=False, default=str) + "\n")
            wrote = True
    return out if wrote else None


def _table_exists(conn, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone() is not None
