"""Compress-Pipeline: RawObservation → CompressedObservation via LLM.

Schritt #61 der Observation Pipeline:
  RawObservation (unkomprimiert) → LLM-Prompt → CompressedObservation (strukturiert)

Trigger: am Session-Ende (session_end → compress_session) oder manuell.
Der LLM-Call läuft über llm_bridge.call_with_tools mit leerer Tool-Liste —
reiner Text-In/JSON-Out.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import secrets
import time
from datetime import datetime, timezone
from typing import Any

from hydrahive.settings import settings
from hydrahive.tools._observations import (
    RawObservation,
    list_raw_observations,
    mark_compressed,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typen
# ---------------------------------------------------------------------------

CompressedObservation = dict[str, Any]

OBS_TYPES = frozenset({
    "file_read", "file_write", "command_run",
    "decision", "discovery", "error", "other",
})

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _compressed_file(agent_id: str, session_id: str) -> Path:
    return settings.agents_dir / agent_id / "compressed" / f"{session_id}.jsonl"


def _save_compressed(agent_id: str, session_id: str, obs: CompressedObservation) -> None:
    path = _compressed_file(agent_id, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obs, ensure_ascii=False) + "\n")


def load_compressed(
    agent_id: str,
    session_id: str,
) -> list[CompressedObservation]:
    """Lädt alle CompressedObservations einer Session."""
    path = _compressed_file(agent_id, session_id)
    if not path.exists():
        return []
    result: list[CompressedObservation] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return result


# ---------------------------------------------------------------------------
# LLM-Prompt
# ---------------------------------------------------------------------------

_COMPRESS_SYSTEM = """\
You are compressing an agent tool-call record into a structured observation.
The input is a single tool-call with its name, arguments, and output.

Extract the following and respond with valid JSON only — no markdown, no explanation:
{
  "type": "<file_read|file_write|command_run|decision|discovery|error|other>",
  "title": "<short description, max 80 chars>",
  "facts": ["<atomic fact 1>", "<atomic fact 2>"],
  "concepts": ["<keyword1>", "<keyword2>"],
  "files": ["<file path if any>"],
  "importance": <integer 1-10>,
  "narrative": "<1-2 sentences what happened and why it matters>"
}

Rules:
- facts: max 5, each is one atomic learned fact
- concepts: max 8, lowercase keywords
- files: only real file paths, empty list if none
- importance: 10=critical decision, 7=significant change, 4=routine read, 1=trivial
- Return ONLY the JSON object, nothing else
"""


def _build_compress_prompt(raw: RawObservation) -> str:
    tool_input = raw.get("tool_input")
    tool_output = raw.get("tool_output")
    hook_type = raw.get("hook_type", "post_tool_use")

    input_str = (
        json.dumps(tool_input, ensure_ascii=False)
        if not isinstance(tool_input, str)
        else tool_input
    ) or "(none)"

    output_str = str(tool_output) if tool_output is not None else "(none)"

    return (
        f"Tool: {raw.get('tool_name', 'unknown')}\n"
        f"Status: {'failure' if hook_type == 'post_tool_failure' else 'success'}\n"
        f"Input:\n{input_str}\n\n"
        f"Output:\n{output_str}"
    )


def _parse_llm_response(text: str, raw: RawObservation) -> dict[str, Any]:
    """Parst die LLM-Antwort. Fällt auf sicheren Default zurück wenn ungültig."""
    text = text.strip()
    # Manchmal wrapped das LLM in ```json ... ```
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            l for l in lines
            if not l.strip().startswith("```")
        ).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("LLM-Compress: ungültiges JSON für obs %s — nutze Fallback", raw.get("id"))
        return _fallback_compressed(raw)

    # Normalisieren + validieren
    obs_type = parsed.get("type", "other")
    if obs_type not in OBS_TYPES:
        obs_type = "other"

    return {
        "type": obs_type,
        "title": str(parsed.get("title", raw.get("tool_name", "unknown")))[:80],
        "facts": [str(f) for f in parsed.get("facts", [])[:5]],
        "concepts": [str(c).lower() for c in parsed.get("concepts", [])[:8]],
        "files": [str(f) for f in parsed.get("files", [])],
        "importance": max(1, min(10, int(parsed.get("importance", 5)))),
        "narrative": str(parsed.get("narrative", ""))[:500],
    }


def _fallback_compressed(raw: RawObservation) -> dict[str, Any]:
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


def _generate_cobs_id() -> str:
    ts = int(time.time() * 1000)
    rand = secrets.token_hex(4)
    return f"cobs_{ts}_{rand}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

async def compress_observation(
    raw: RawObservation,
    *,
    model: str,
) -> CompressedObservation:
    """
    Komprimiert eine einzelne RawObservation via LLM.
    Gibt CompressedObservation zurück (ohne Storage-Seiteneffekt).
    """
    from hydrahive.runner.llm_bridge import call_with_tools

    prompt = _build_compress_prompt(raw)
    try:
        blocks, _ = await call_with_tools(
            model=model,
            system_prompt=_COMPRESS_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            tools=[],
            temperature=0.0,
            max_tokens=512,
        )
        text = "".join(
            b.get("text", "") for b in blocks if b.get("type") == "text"
        )
        parsed = _parse_llm_response(text, raw)
    except Exception as e:
        logger.warning("compress_observation LLM-Fehler für %s: %s — nutze Fallback", raw.get("id"), e)
        parsed = _fallback_compressed(raw)

    cobs: CompressedObservation = {
        "id": _generate_cobs_id(),
        "session_id": raw.get("session_id"),
        "agent_id": raw.get("agent_id"),
        "raw_observation_id": raw.get("id"),
        "timestamp": _now_iso(),
        **parsed,
    }
    return cobs


async def compress_session(
    agent_id: str,
    session_id: str,
    *,
    model: str,
) -> list[CompressedObservation]:
    """
    Komprimiert alle noch unkomprimierten Observations einer Session.
    Speichert CompressedObservations in JSONL.
    Markiert RawObservations als compressed.
    Gibt die neu erstellten CompressedObservations zurück.

    Wird vom Runner am Session-Ende aufgerufen (aus session_end-Hook).
    Kann auch manuell aufgerufen werden.
    """
    raws = list_raw_observations(agent_id, session_id, uncompressed_only=True)
    if not raws:
        return []

    results: list[CompressedObservation] = []
    for raw in raws:
        cobs = await compress_observation(raw, model=model)
        _save_compressed(agent_id, session_id, cobs)
        mark_compressed(agent_id, session_id, raw["id"], cobs["id"])
        results.append(cobs)
        logger.debug("compress_session: %s → %s", raw["id"], cobs["id"])

    logger.info(
        "compress_session %s: %d Observations komprimiert", session_id, len(results)
    )

    # Auto-Crystallize wenn genug Observations vorhanden
    try:
        from hydrahive.tools._crystallize import crystallize_session, MIN_OBSERVATIONS
        total_compressed = results  # nur neu komprimierte — laden wir nochmal alle
        from hydrahive.tools._compress import load_compressed
        all_obs = load_compressed(agent_id, session_id)
        if len(all_obs) >= MIN_OBSERVATIONS:
            import asyncio as _asyncio
            _asyncio.create_task(
                crystallize_session(agent_id, session_id, model=model)
            )
    except Exception as _ce:
        logger.warning("auto-crystallize fehlgeschlagen (nicht fatal): %s", _ce)

    return results
