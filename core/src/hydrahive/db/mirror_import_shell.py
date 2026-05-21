"""Shell-History → PostgreSQL-Mirror Import.

Parst bash_history / zsh_history (inkl. Extended-History-Timestamps) und
schreibt Befehle als Events in den Mirror.

Bash-Format:          eine Zeile pro Befehl, optional `#<unix-ts>` davor
Zsh-Extended-Format:  `: <unix-ts>:<elapsed>;<command>`
ON CONFLICT DO NOTHING — idempotent, Dedup über uuid5.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone, date
from io import StringIO

logger = logging.getLogger(__name__)

# Zsh extended history: `: 1716000000:0;some command`
_ZSH_TS_RE = re.compile(r"^: (\d+):\d+;(.+)$")

# Befehle die wahrscheinlich Secrets enthalten — nicht importieren
_SENSITIVE_RE = re.compile(
    r"(?i)(password|passwd|secret|token|api[_\-]?key|private[_\-]?key"
    r"|aws[_\-]?secret|aws[_\-]?access|bearer|credential"
    r"|[_=\s]pass\b|-p\s+\S+\s+\S+@)",
)


def parse_history(content: str, username: str) -> list[dict]:
    lines = content.splitlines()
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()

    i = 0
    while i < len(lines):
        line = lines[i]

        # Zsh extended: `: timestamp:elapsed;command`
        m = _ZSH_TS_RE.match(line)
        if m:
            ts = datetime.fromtimestamp(int(m.group(1)), tz=timezone.utc)
            cmd = m.group(2).strip()
            i += 1
        # Bash with timestamp: `#unix_timestamp` on its own line
        elif line.startswith("#") and line[1:].isdigit() and i + 1 < len(lines):
            try:
                ts = datetime.fromtimestamp(int(line[1:]), tz=timezone.utc)
            except (ValueError, OSError):
                ts = datetime.now(timezone.utc)
            i += 1
            cmd = lines[i].strip() if i < len(lines) else ""
            i += 1
        else:
            cmd = line.strip()
            ts = datetime.now(timezone.utc)
            i += 1

        if not cmd or cmd.startswith("#"):
            continue
        if _SENSITIVE_RE.search(cmd):
            continue

        day = ts.strftime("%Y-%m-%d")
        dedup_key = (username, day, cmd[:200])
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        row_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"shell:{username}:{day}:{cmd[:200]}"))
        rows.append({
            "id": row_id,
            "session_id": f"shell-history",
            "event_type": "shell_command",
            "text": cmd[:500],
            "username": username,
            "tool_input": json.dumps({"command": cmd[:500], "cwd": None}),
            "created_at": ts,
        })

    return rows


async def run_shell_import(content: str, username: str) -> dict:
    rows = await asyncio.to_thread(parse_history, content, username)
    if not rows:
        return {"ok": True, "inserted": 0, "skipped_sensitive": 0}

    from hydrahive.db import mirror
    if not mirror._pool:
        raise RuntimeError("PG-Mirror nicht aktiv")

    async with mirror._pool.acquire() as conn:
        await conn.executemany("""
            INSERT INTO events (id, message_id, session_id, block_index, chunk_index,
              chunk_total, username, agent_id, agent_name, project_id, event_type,
              text, tool_name, tool_use_id, tool_input, tool_output, is_error,
              token_count, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15::jsonb,$16,$17,$18,$19)
            ON CONFLICT (id) DO NOTHING
        """, [
            (r["id"], r["id"], r["session_id"], 0, 0, 1,
             r["username"], None, None, None,
             r["event_type"], r["text"], None, None,
             r["tool_input"], None, False, None, r["created_at"])
            for r in rows
        ])

    logger.info("Shell-Import: %d Befehle für %s importiert", len(rows), username)
    return {"ok": True, "inserted": len(rows)}
