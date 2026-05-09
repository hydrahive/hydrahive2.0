"""Compress-Pipeline: RawObservation → CompressedObservation via LLM.

Schritt #61 der Observation Pipeline:
  RawObservation (unkomprimiert) → LLM-Prompt → CompressedObservation (strukturiert)

Trigger: am Session-Ende (session_end → compress_session) oder manuell.
Der LLM-Call läuft über llm_bridge.call_with_tools mit leerer Tool-Liste —
reiner Text-In/JSON-Out.

Storage in `_compress_storage.py`, Prompts/Parsing in `_compress_prompts.py`.
"""
from __future__ import annotations

import logging

from hydrahive.tools._compress_prompts import (
    COMPRESS_BATCH_SIZE,
    COMPRESS_SYSTEM,
    build_batch_prompt,
    fallback_compressed,
    generate_cobs_id,
    now_iso,
    parse_batch_response,
)
from hydrahive.tools._compress_storage import (
    CompressedObservation,
    load_compressed,
    save_compressed,
)
from hydrahive.tools._observations import (
    RawObservation,
    list_raw_observations,
    mark_compressed,
)

logger = logging.getLogger(__name__)


__all__ = ["CompressedObservation", "load_compressed", "compress_session"]


async def _compress_batch(
    raws: list[RawObservation],
    *,
    model: str,
    agent_id: str,
    session_id: str,
) -> list[CompressedObservation]:
    """Komprimiert eine Gruppe von RawObservations in einem einzigen LLM-Call."""
    from hydrahive.runner.llm_bridge import call_with_tools

    prompt = build_batch_prompt(raws)
    max_tokens = min(8192, len(raws) * 220 + 256)
    try:
        blocks, _ = await call_with_tools(
            model=model,
            system_prompt=COMPRESS_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            tools=[],
            temperature=0.0,
            max_tokens=max_tokens,
        )
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        parsed_list = parse_batch_response(text, raws)
    except Exception as e:
        logger.warning("compress batch LLM-Fehler (%d obs): %s — Fallback", len(raws), e)
        parsed_list = [fallback_compressed(r) for r in raws]

    results: list[CompressedObservation] = []
    for raw, parsed in zip(raws, parsed_list):
        cobs: CompressedObservation = {
            "id": generate_cobs_id(),
            "session_id": raw.get("session_id"),
            "agent_id": raw.get("agent_id"),
            "raw_observation_id": raw.get("id"),
            "timestamp": now_iso(),
            **parsed,
        }
        save_compressed(agent_id, session_id, cobs)
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
    for i in range(0, len(raws), COMPRESS_BATCH_SIZE):
        batch = raws[i:i + COMPRESS_BATCH_SIZE]
        batch_results = await _compress_batch(batch, model=model, agent_id=agent_id, session_id=session_id)
        results.extend(batch_results)
        logger.debug("compress_session batch %d-%d: %d komprimiert", i, i + len(batch), len(batch_results))

    logger.info(
        "compress_session %s: %d Observations in %d Batch(es) komprimiert",
        session_id, len(results), max(1, (len(raws) + COMPRESS_BATCH_SIZE - 1) // COMPRESS_BATCH_SIZE),
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
