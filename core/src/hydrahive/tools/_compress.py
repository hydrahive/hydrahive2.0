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

_COMPRESS_BATCH_SIZE = 30  # max Observations pro LLM-Call


def _build_batch_prompt(raws: list[RawObservation]) -> str:
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


def _parse_batch_response(text: str, raws: list[RawObservation]) -> list[dict[str, Any]]:
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
        return [_fallback_compressed(r) for r in raws]

    results: list[dict[str, Any]] = []
    raw_by_id = {r.get("id"): r for r in raws}

    for item, raw in zip(parsed, raws):
        if not isinstance(item, dict):
            results.append(_fallback_compressed(raw))
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
        results.append(_fallback_compressed(raws[len(results)]))

    return results


def _parse_llm_response(text: str, raw: RawObservation) -> dict[str, Any]:
    """Einzelner Parse für compress_observation (manueller Aufruf). Batch-Pfad nutzt _parse_batch_response."""
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(l for l in text.splitlines() if not l.strip().startswith("```")).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("LLM-Compress: ungültiges JSON für obs %s — nutze Fallback", raw.get("id"))
        return _fallback_compressed(raw)

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


async def _compress_batch(
    raws: list[RawObservation],
    *,
    model: str,
    agent_id: str,
    session_id: str,
) -> list[CompressedObservation]:
    """Komprimiert eine Gruppe von RawObservations in einem einzigen LLM-Call."""
    from hydrahive.runner.llm_bridge import call_with_tools

    prompt = _build_batch_prompt(raws)
    max_tokens = min(8192, len(raws) * 220 + 256)
    try:
        blocks, _ = await call_with_tools(
            model=model,
            system_prompt=_COMPRESS_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            tools=[],
            temperature=0.0,
            max_tokens=max_tokens,
        )
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        parsed_list = _parse_batch_response(text, raws)
    except Exception as e:
        logger.warning("compress batch LLM-Fehler (%d obs): %s — Fallback", len(raws), e)
        parsed_list = [_fallback_compressed(r) for r in raws]

    results: list[CompressedObservation] = []
    for raw, parsed in zip(raws, parsed_list):
        cobs: CompressedObservation = {
            "id": _generate_cobs_id(),
            "session_id": raw.get("session_id"),
            "agent_id": raw.get("agent_id"),
            "raw_observation_id": raw.get("id"),
            "timestamp": _now_iso(),
            **parsed,
        }
        _save_compressed(agent_id, session_id, cobs)
        mark_compressed(agent_id, session_id, raw["id"], cobs["id"])
        results.append(cobs)
    return results


async def compress_session(
    agent_id: str,
    session_id: str,
    *,
    model: str,
) -> list[CompressedObservation]:
    """
    Komprimiert alle noch unkomprimierten Observations einer Session.
    Nutzt Batch-Compression: ceil(N/30) LLM-Calls statt N einzelne.
    Speichert CompressedObservations in JSONL und markiert Raws als compressed.
    """
    raws = list_raw_observations(agent_id, session_id, uncompressed_only=True)
    if not raws:
        return []

    results: list[CompressedObservation] = []
    for i in range(0, len(raws), _COMPRESS_BATCH_SIZE):
        batch = raws[i:i + _COMPRESS_BATCH_SIZE]
        batch_results = await _compress_batch(batch, model=model, agent_id=agent_id, session_id=session_id)
        results.extend(batch_results)
        logger.debug("compress_session batch %d-%d: %d komprimiert", i, i + len(batch), len(batch_results))

    logger.info(
        "compress_session %s: %d Observations in %d Batch(es) komprimiert",
        session_id, len(results), max(1, (len(raws) + _COMPRESS_BATCH_SIZE - 1) // _COMPRESS_BATCH_SIZE),
    )

    # Auto-Crystallize wenn genug Observations vorhanden
    try:
        from hydrahive.tools._crystallize import crystallize_session, MIN_OBSERVATIONS
        from hydrahive.tools._sessions import session_get
        all_obs = load_compressed(agent_id, session_id)
        if len(all_obs) >= MIN_OBSERVATIONS:
            session = session_get(agent_id, session_id)
            project = session.get("project") if session else None
            import asyncio as _asyncio
            _asyncio.create_task(
                crystallize_session(agent_id, session_id, model=model, project=project)
            )
    except Exception as _ce:
        logger.warning("auto-crystallize fehlgeschlagen (nicht fatal): %s", _ce)

    return results
