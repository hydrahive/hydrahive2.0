"""Git-History → PostgreSQL-Mirror Import.

Liest git log aus einem Repo und schreibt Commits als Events in den Mirror.
ON CONFLICT DO NOTHING — bereits vorhandene Commits bleiben unverändert.

event_type = "git_commit"
text       = Commit-Message
tool_name  = Branch/Ref (erstes ref)
tool_input = {"hash": ..., "author": ..., "files_changed": ..., "insertions": ..., "deletions": ...}
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_running: bool = False
_progress: dict = {"commits": 0, "total": 0, "repo": ""}


def git_import_status() -> dict:
    return {"running": _running, **_progress}


async def run_git_import(repo_path: str) -> None:
    global _running, _progress
    if _running:
        return
    _running = True
    _progress = {"commits": 0, "total": 0, "repo": repo_path}
    try:
        from hydrahive.db import mirror
        if not mirror._pool:
            raise RuntimeError("PG-Mirror nicht aktiv")

        commits = await asyncio.to_thread(_read_git_log, repo_path)
        _progress["total"] = len(commits)
        logger.info("Git-Import: %d Commits aus %s", len(commits), repo_path)

        rows = []
        for c in commits:
            rows.append(_commit_to_row(c))
            if len(rows) >= 200:
                await _insert_rows(mirror._pool, rows)
                _progress["commits"] += len(rows)
                rows = []
        if rows:
            await _insert_rows(mirror._pool, rows)
            _progress["commits"] += len(rows)

        logger.info("Git-Import abgeschlossen: %d Commits eingefügt", _progress["commits"])
    except Exception as e:
        logger.warning("Git-Import fehlgeschlagen: %s", e)
    finally:
        _running = False


def _read_git_log(repo_path: str) -> list[dict]:
    sep = "\x1f"
    fmt = sep.join(["%H", "%ae", "%an", "%aI", "%s", "%D"])
    result = subprocess.run(
        ["git", "-C", repo_path, "log", "--all", f"--format={fmt}", "--numstat"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git log fehlgeschlagen: {result.stderr[:200]}")

    commits = []
    current: dict | None = None
    for line in result.stdout.splitlines():
        if sep in line:
            if current:
                commits.append(current)
            parts = line.split(sep, 5)
            if len(parts) < 6:
                continue
            current = {
                "hash": parts[0], "email": parts[1], "author": parts[2],
                "timestamp": parts[3], "message": parts[4], "refs": parts[5],
                "files": 0, "insertions": 0, "deletions": 0,
            }
        elif current and line.strip():
            # numstat lines: "additions\tdeletions\tfilename"
            m = re.match(r"^(\d+|-)\t(\d+|-)\t(.+)$", line)
            if m:
                ins = int(m.group(1)) if m.group(1) != "-" else 0
                dels = int(m.group(2)) if m.group(2) != "-" else 0
                current["files"] += 1
                current["insertions"] += ins
                current["deletions"] += dels
    if current:
        commits.append(current)
    return commits


def _commit_to_row(c: dict) -> dict:
    try:
        ts = datetime.fromisoformat(c["timestamp"])
    except ValueError:
        ts = datetime.now(timezone.utc)

    refs = c.get("refs", "").strip()
    branch = refs.split(",")[0].strip() if refs else ""

    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"git:{c['hash']}")),
        "message_id": c["hash"],
        "session_id": "git-history",
        "block_index": 0,
        "chunk_index": 0,
        "chunk_total": 1,
        "username": c["email"],
        "agent_id": None,
        "agent_name": c["author"],
        "project_id": None,
        "event_type": "git_commit",
        "text": c["message"],
        "tool_name": branch or None,
        "tool_use_id": c["hash"],
        "tool_input": json.dumps({
            "hash": c["hash"], "author": c["author"], "email": c["email"],
            "refs": c.get("refs", ""),
            "files_changed": c["files"],
            "insertions": c["insertions"],
            "deletions": c["deletions"],
        }),
        "tool_output": None,
        "is_error": False,
        "token_count": None,
        "created_at": ts,
    }


async def _insert_rows(pool, rows: list[dict]) -> None:
    async with pool.acquire() as conn:
        await conn.executemany("""
            INSERT INTO events (id, message_id, session_id, block_index, chunk_index,
              chunk_total, username, agent_id, agent_name, project_id, event_type,
              text, tool_name, tool_use_id, tool_input, tool_output, is_error,
              token_count, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15::jsonb,$16,$17,$18,$19)
            ON CONFLICT (id) DO NOTHING
        """, [
            (r["id"], r["message_id"], r["session_id"], r["block_index"], r["chunk_index"],
             r["chunk_total"], r["username"], r["agent_id"], r["agent_name"], r["project_id"],
             r["event_type"], r["text"], r["tool_name"], r["tool_use_id"], r["tool_input"],
             r["tool_output"], r["is_error"], r["token_count"], r["created_at"])
            for r in rows
        ])
