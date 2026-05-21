"""JSONL Token-Usage → PostgreSQL-Mirror Import.

Liest alle JSONL-Transcript-Dateien aus agents/{id}/ und schreibt
LLM-Calls (usage-Felder) in die llm_calls-Tabelle.
ON CONFLICT DO NOTHING — bereits vorhandene Einträge bleiben.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_running: bool = False
_progress: dict = {"files": 0, "calls": 0, "total_files": 0}


def jsonl_import_status() -> dict:
    return {"running": _running, **_progress}


async def run_jsonl_import() -> None:
    global _running, _progress
    if _running:
        return
    _running = True
    _progress = {"files": 0, "calls": 0, "total_files": 0}
    try:
        from hydrahive.db import mirror
        from hydrahive.settings import settings
        if not mirror._pool:
            raise RuntimeError("PG-Mirror nicht aktiv")

        jsonl_files = list(Path(settings.agents_dir).rglob("*.jsonl"))
        _progress["total_files"] = len(jsonl_files)
        logger.info("JSONL-Import: %d Dateien gefunden", len(jsonl_files))

        for path in jsonl_files:
            rows = await asyncio.to_thread(_parse_jsonl, path)
            if rows:
                await _insert_rows(mirror._pool, rows)
                _progress["calls"] += len(rows)
            _progress["files"] += 1

        logger.info("JSONL-Import abgeschlossen: %d LLM-Calls", _progress["calls"])
    except Exception as e:
        logger.warning("JSONL-Import fehlgeschlagen: %s", e)
    finally:
        _running = False


def _parse_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        agent_id = path.parts[-3] if len(path.parts) >= 3 else None
        session_id = path.stem

        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                usage = entry.get("usage") or {}
                if not usage:
                    continue

                role = entry.get("role", "")
                if role != "assistant":
                    continue

                prompt_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
                completion_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or 0
                if not prompt_tokens and not completion_tokens:
                    continue

                ts_raw = entry.get("created_at") or entry.get("timestamp")
                try:
                    ts = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now(timezone.utc)
                except (ValueError, TypeError):
                    ts = datetime.now(timezone.utc)

                model = entry.get("model") or entry.get("llm_model") or "unknown"
                provider = _guess_provider(model)

                row_id = str(uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"jsonl:{session_id}:{entry.get('id', '')or ts.isoformat()}"
                ))
                rows.append({
                    "id": row_id,
                    "session_id": session_id,
                    "created_at": ts,
                    "agent_id": agent_id,
                    "user_id": entry.get("username") or entry.get("user_id"),
                    "provider": provider,
                    "model": model,
                    "temperature": entry.get("temperature"),
                    "max_tokens": entry.get("max_tokens"),
                    "reasoning_effort": entry.get("reasoning_effort"),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "cache_read_tokens": usage.get("cache_read_input_tokens") or 0,
                    "cache_creation_tokens": usage.get("cache_creation_input_tokens") or 0,
                    "stop_reason": entry.get("stop_reason"),
                    "ttft_ms": None,
                    "total_ms": None,
                    "cost_micros": None,
                    "turn_in_session": entry.get("turn_index"),
                })
    except Exception as e:
        logger.debug("JSONL parse Fehler %s: %s", path, e)
    return rows


def _guess_provider(model: str) -> str:
    m = model.lower()
    if "claude" in m:
        return "anthropic"
    if "minimax" in m or "m2." in m:
        return "minimax"
    if "gpt" in m or "o1" in m or "o3" in m:
        return "openai"
    if "gemini" in m:
        return "google"
    return "unknown"


async def _insert_rows(pool, rows: list[dict]) -> None:
    async with pool.acquire() as conn:
        await conn.executemany("""
            INSERT INTO llm_calls (
              id, session_id, created_at, agent_id, user_id, provider, model,
              temperature, max_tokens, reasoning_effort, prompt_tokens,
              completion_tokens, cache_read_tokens, cache_creation_tokens,
              stop_reason, ttft_ms, total_ms, cost_micros, turn_in_session
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
            ON CONFLICT (id) DO NOTHING
        """, [
            (r["id"], r["session_id"], r["created_at"], r["agent_id"], r["user_id"],
             r["provider"], r["model"], r["temperature"], r["max_tokens"],
             r["reasoning_effort"], r["prompt_tokens"], r["completion_tokens"],
             r["cache_read_tokens"], r["cache_creation_tokens"], r["stop_reason"],
             r["ttft_ms"], r["total_ms"], r["cost_micros"], r["turn_in_session"])
            for r in rows
        ])
