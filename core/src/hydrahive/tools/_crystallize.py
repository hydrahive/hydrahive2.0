"""Crystallize-Pipeline: CompressedObservations → Crystal + Lessons via LLM.

Schritt #62 der Observation Pipeline:
  CompressedObservations (strukturiert) → LLM-Prompt → Crystal (Session-Digest)
  + Lessons werden als Memory-Einträge gespeichert (confidence=0.6)

Trigger:
  - Automatisch am Session-Ende wenn >= MIN_OBSERVATIONS CompressedObservations
    vorhanden (wird von compress_session() in _compress.py gerufen)
  - Manuell via crystallize_session() Tool (Agent kann direkt aufrufen)

Storage in `_crystallize_storage.py`, Prompts/Parsing in `_crystallize_prompts.py`.
"""
from __future__ import annotations

import logging

from hydrahive.tools._crystallize_prompts import (
    CRYSTALLIZE_SYSTEM,
    build_chain_text,
    fallback_digest,
    fingerprint,
    generate_crystal_id,
    now_iso,
    parse_llm_response,
)
from hydrahive.tools._crystallize_storage import (
    Crystal,
    get_crystal,
    list_crystals,
    save_crystal,
)

logger = logging.getLogger(__name__)


# Mindestanzahl CompressedObservations für Auto-Crystallize
MIN_OBSERVATIONS = 5


__all__ = [
    "Crystal",
    "MIN_OBSERVATIONS",
    "list_crystals",
    "get_crystal",
    "save_crystal",
    "crystallize_session",
]


def _save_lessons(
    agent_id: str,
    lessons: list[str],
    project: str | None,
) -> list[str]:
    """
    Speichert Lessons als Memory-Einträge (confidence=0.6, key=lesson.<fp>).
    Ein File-Read+Write für die ganze Batch (vs. N Rewrites pro Lesson).
    Gibt Liste der gespeicherten Keys zurück.
    """
    from hydrahive.tools._memory_store import write_keys_bulk

    entries: list[dict] = []
    for lesson in lessons:
        if not lesson.strip():
            continue
        entries.append({
            "key": f"lesson.{fingerprint(lesson)}",
            "content": lesson,
            "confidence": 0.6,
            "project": project,
            "check_contradictions": False,
        })
    if not entries:
        return []
    try:
        write_keys_bulk(agent_id, entries)
    except Exception as e:
        logger.warning("_save_lessons: Bulk-Write fehlgeschlagen: %s", e)
        return []
    return [e["key"] for e in entries]


async def crystallize_session(
    agent_id: str,
    session_id: str,
    *,
    model: str,
    project: str | None = None,
    force: bool = False,
) -> Crystal | None:
    """
    Kristallisiert eine Session: alle CompressedObservations → Crystal + Lessons.

    - Lädt CompressedObservations via load_compressed()
    - Baut Chain-Text und ruft LLM auf
    - Speichert Crystal in crystals.jsonl
    - Speichert Lessons als Memory-Einträge (confidence=0.6)
    - Gibt Crystal zurück, oder None wenn zu wenig Observations (außer force=True)

    force=True: auch bei < MIN_OBSERVATIONS kristallisieren UND einen
    bestehenden Crystal überschreiben (append-only versioniert in jsonl).
    """
    from hydrahive.runner.llm_bridge import call_with_tools
    from hydrahive.tools._compress import load_compressed

    if not force:
        existing = get_crystal(agent_id, session_id)
        if existing is not None:
            logger.info("crystallize_session %s: bereits kristallisiert — skip", session_id)
            return existing

    observations = load_compressed(agent_id, session_id)
    if not observations:
        logger.debug("crystallize_session %s: keine CompressedObservations", session_id)
        return None

    if len(observations) < MIN_OBSERVATIONS and not force:
        logger.debug(
            "crystallize_session %s: nur %d Observations (< %d) — skip",
            session_id, len(observations), MIN_OBSERVATIONS,
        )
        return None

    chain_text = build_chain_text(observations)

    try:
        blocks, _, _ = await call_with_tools(
            model=model,
            system_prompt=CRYSTALLIZE_SYSTEM,
            messages=[{"role": "user", "content": chain_text}],
            tools=[],
            temperature=0.0,
            max_tokens=1024,
        )
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        digest = parse_llm_response(text, session_id)
    except Exception as e:
        logger.warning("crystallize_session LLM-Fehler für %s: %s — nutze Fallback", session_id, e)
        digest = fallback_digest(session_id)

    # Deduplizierte files aus Observations + LLM-Ergebnis zusammenführen
    all_files: list[str] = list(digest["files_affected"])
    seen: set[str] = set(all_files)
    for obs in observations:
        for f in (obs.get("files") or []):
            if f not in seen:
                all_files.append(f)
                seen.add(f)

    crystal: Crystal = {
        "id": generate_crystal_id(),
        "session_id": session_id,
        "agent_id": agent_id,
        "project": project,
        "created_at": now_iso(),
        "narrative": digest["narrative"],
        "key_outcomes": digest["key_outcomes"],
        "files_affected": all_files,
        "lessons": digest["lessons"],
        "source_observation_ids": [o["id"] for o in observations],
        "observation_count": len(observations),
    }

    save_crystal(agent_id, crystal)

    # Lessons → Memory
    saved_lesson_keys = _save_lessons(agent_id, digest["lessons"], project)
    if saved_lesson_keys:
        logger.info(
            "crystallize_session %s: %d Lessons gespeichert: %s",
            session_id, len(saved_lesson_keys), saved_lesson_keys,
        )

    logger.info(
        "crystallize_session %s: Crystal %s erstellt (%d obs, %d lessons)",
        session_id, crystal["id"], len(observations), len(digest["lessons"]),
    )
    return crystal
