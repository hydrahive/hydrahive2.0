"""Compress-Pipeline — LLM-Prompt-Aufbau, Response-Parsing, Fallbacks."""
from __future__ import annotations

import json
import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Any

from hydrahive.tools._observations import RawObservation

logger = logging.getLogger(__name__)


OBS_TYPES = frozenset({
    "file_read", "file_write", "command_run",
    "decision", "discovery", "error", "other",
})

COMPRESS_BATCH_SIZE = 30  # max Observations pro LLM-Call

COMPRESS_SYSTEM = """\
You are compressing agent tool-call records into structured observations.
The input is a numbered list of tool-calls. Return a JSON ARRAY with one object
per tool-call, in the same order — no markdown, no explanation.

Each object must have:
{
  "id": "<the id value from the input>",
  "type": "<file_read|file_write|command_run|decision|discovery|error|other>",
  "title": "<short description, max 80 chars>",
  "facts": ["<atomic fact>"],
  "concepts": ["<keyword>"],
  "files": ["<file path if any>"],
  "importance": <integer 1-10>,
  "narrative": "<1-2 sentences what happened and why it matters>"
}

Rules:
- facts: max 5, each is one atomic learned fact
- concepts: max 8, lowercase keywords
- files: only real file paths, empty list if none
- importance: 10=critical decision, 7=significant change, 4=routine read, 1=trivial
- Return ONLY the JSON array, nothing else
"""


def build_batch_prompt(raws: list[RawObservation]) -> str:
    parts: list[str] = []
    for i, raw in enumerate(raws, 1):
        tool_input = raw.get("tool_input")
        tool_output = raw.get("tool_output")
        hook_type = raw.get("hook_type", "post_tool_use")
        input_str = (
            json.dumps(tool_input, ensure_ascii=False)
            if not isinstance(tool_input, str)
            else tool_input
        ) or "(none)"
        output_str = str(tool_output) if tool_output is not None else "(none)"
        parts.append(
            f"## {i}. id={raw.get('id', '')} tool={raw.get('tool_name', 'unknown')} "
            f"status={'failure' if hook_type == 'post_tool_failure' else 'success'}\n"
            f"Input: {input_str}\nOutput: {output_str}"
        )
    return "\n\n".join(parts)


def parse_batch_response(text: str, raws: list[RawObservation]) -> list[dict[str, Any]]:
    """Parst JSON-Array aus Batch-Antwort. Fällt pro Eintrag auf Fallback zurück."""
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(l for l in text.splitlines() if not l.strip().startswith("```")).strip()
    try:
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError("expected list")
    except (json.JSONDecodeError, ValueError):
        logger.warning("LLM-Compress batch: ungültiges JSON — Fallback für alle %d obs", len(raws))
        return [fallback_compressed(r) for r in raws]

    results: list[dict[str, Any]] = []
    raw_by_id = {r.get("id"): r for r in raws}

    for item, raw in zip(parsed, raws):
        if not isinstance(item, dict):
            results.append(fallback_compressed(raw))
            continue
        obs_id = item.get("id") or raw.get("id", "")
        matched_raw = raw_by_id.get(obs_id, raw)
        obs_type = item.get("type", "other")
        if obs_type not in OBS_TYPES:
            obs_type = "other"
        results.append({
            "type": obs_type,
            "title": str(item.get("title", matched_raw.get("tool_name", "unknown")))[:80],
            "facts": [str(f) for f in item.get("facts", [])[:5]],
            "concepts": [str(c).lower() for c in item.get("concepts", [])[:8]],
            "files": [str(f) for f in item.get("files", [])],
            "importance": max(1, min(10, int(item.get("importance", 5)))),
            "narrative": str(item.get("narrative", ""))[:500],
        })

    # Wenn LLM weniger Einträge zurückgibt als erwartet, Rest auffüllen
    while len(results) < len(raws):
        results.append(fallback_compressed(raws[len(results)]))

    return results


def fallback_compressed(raw: RawObservation) -> dict[str, Any]:
    """Minimaler Fallback wenn LLM-Parsing fehlschlägt."""
    return {
        "type": "other",
        "title": raw.get("tool_name", "unknown")[:80],
        "facts": [],
        "concepts": [],
        "files": [],
        "importance": 3,
        "narrative": f"Tool '{raw.get('tool_name')}' aufgerufen.",
    }


def generate_cobs_id() -> str:
    ts = int(time.time() * 1000)
    rand = secrets.token_hex(4)
    return f"cobs_{ts}_{rand}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
