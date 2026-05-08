"""Crystallize-Pipeline: CompressedObservations → Crystal + Lessons via LLM.

Schritt #62 der Observation Pipeline:
  CompressedObservations (strukturiert) → LLM-Prompt → Crystal (Session-Digest)
  + Lessons werden als Memory-Einträge gespeichert (confidence=0.6)

Trigger:
  - Automatisch am Session-Ende wenn >= MIN_OBSERVATIONS CompressedObservations
    vorhanden (wird von compress_session() in _compress.py gerufen)
  - Manuell via crystallize_session() Tool (Agent kann direkt aufrufen)
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

# Mindestanzahl CompressedObservations für Auto-Crystallize
MIN_OBSERVATIONS = 5

# ---------------------------------------------------------------------------
# Typen
# ---------------------------------------------------------------------------

Crystal = dict[str, Any]

# ---------------------------------------------------------------------------
# LLM-Prompt
# ---------------------------------------------------------------------------

_CRYSTALLIZE_SYSTEM = """\
You are summarizing a completed chain of agent actions into a compact digest.
The input is a structured list of observations from a single session.

Extract the following and respond with valid JSON only — no markdown, no explanation:
{
  "narrative": "<1-2 sentences: what was accomplished overall>",
  "key_outcomes": ["<outcome 1>", "<outcome 2>"],
  "files_affected": ["<file path 1>", "<file path 2>"],
  "lessons": ["<lesson or pattern worth remembering>"]
}

Rules:
- narrative: concise, factual, max 200 chars
- key_outcomes: max 8, each one concrete result or decision
- files_affected: deduplicated real file paths only, empty list if none
- lessons: max 5, generalizable insights — not session-specific facts
- Return ONLY the JSON object, nothing else
"""


def build_chain_text(observations: list[dict[str, Any]]) -> str:
    """Baut aus CompressedObservations einen strukturierten Prompt-Input."""
    if not observations:
        return "(no observations)"

    lines: list[str] = ["## Session Observations\n"]
    for obs in observations:
        obs_type = obs.get("type", "other")
        title = obs.get("title", "unknown")
        lines.append(f"### {obs_type} — {title}")

        facts = obs.get("facts") or []
        for fact in facts:
            lines.append(f"  {fact}")

        narrative = obs.get("narrative", "")
        if narrative:
            lines.append(f"  → {narrative}")

        files = obs.get("files") or []
        if files:
            lines.append(f"  files: {', '.join(files)}")

        importance = obs.get("importance", 5)
        lines.append(f"  importance: {importance}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def fingerprint(text: str) -> str:
    """SHA256[:12] des Textes — stabiler Key für Lesson-Dedup."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _generate_crystal_id() -> str:
    ts = int(time.time() * 1000)
    rand = secrets.token_hex(4)
    return f"crys_{ts}_{rand}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_llm_response(text: str, session_id: str) -> dict[str, Any]:
    """Parst die LLM-Antwort. Fällt auf sicheren Default zurück wenn ungültig."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            l for l in lines if not l.strip().startswith("```")
        ).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("LLM-Crystallize: ungültiges JSON für session %s — nutze Fallback", session_id)
        return _fallback_digest(session_id)

    return {
        "narrative": str(parsed.get("narrative", ""))[:200],
        "key_outcomes": [str(o) for o in parsed.get("key_outcomes", [])[:8]],
        "files_affected": [str(f) for f in parsed.get("files_affected", [])],
        "lessons": [str(l) for l in parsed.get("lessons", [])[:5]],
    }


def _fallback_digest(session_id: str) -> dict[str, Any]:
    """Minimaler Fallback wenn LLM-Parsing fehlschlägt."""
    return {
        "narrative": f"Session {session_id} abgeschlossen.",
        "key_outcomes": [],
        "files_affected": [],
        "lessons": [],
    }


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _crystals_file(agent_id: str) -> Path:
    """Alle Crystals eines Agents in einer JSONL-Datei."""
    return settings.agents_dir / agent_id / "crystals.jsonl"


def save_crystal(agent_id: str, crystal: Crystal) -> None:
    """Speichert einen Crystal append-only in crystals.jsonl."""
    path = _crystals_file(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(crystal, ensure_ascii=False) + "\n")


def list_crystals(
    agent_id: str,
    project: str | None = None,
    limit: int = 20,
) -> list[Crystal]:
    """Lädt Crystals eines Agents. Optional nach project gefiltert, neueste zuerst."""
    path = _crystals_file(agent_id)
    if not path.exists():
        return []

    results: list[Crystal] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if project is not None and entry.get("project") != project:
                continue
            results.append(entry)
    except OSError:
        return []

    # Neueste zuerst, dann limit anwenden
    results.reverse()
    return results[:limit]


def get_crystal(agent_id: str, session_id: str) -> Crystal | None:
    """Gibt den Crystal einer bestimmten Session zurück (oder None)."""
    path = _crystals_file(agent_id)
    if not path.exists():
        return None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("session_id") == session_id:
                    return entry
            except json.JSONDecodeError:
                continue
    except OSError:
        return None
    return None


# ---------------------------------------------------------------------------
# Lessons → Memory
# ---------------------------------------------------------------------------

def _save_lessons(
    agent_id: str,
    lessons: list[str],
    project: str | None,
) -> list[str]:
    """
    Speichert Lessons als Memory-Einträge (confidence=0.6, key=lesson.<fp>).
    Gibt Liste der gespeicherten Keys zurück.
    """
    from hydrahive.tools._memory_store import write_key

    saved: list[str] = []
    for lesson in lessons:
        if not lesson.strip():
            continue
        key = f"lesson.{fingerprint(lesson)}"
        try:
            write_key(
                agent_id,
                key,
                lesson,
                confidence=0.6,
                project=project,
                check_contradictions=False,  # Lessons nicht gegen sich selbst prüfen
            )
            saved.append(key)
        except Exception as e:
            logger.warning("_save_lessons: Fehler bei '%s': %s", key, e)
    return saved


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

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

    force=True: auch bei < MIN_OBSERVATIONS kristallisieren (für manuellen Aufruf).
    """
    from hydrahive.runner.llm_bridge import call_with_tools
    from hydrahive.tools._compress import load_compressed

    # Bereits kristallisiert?
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
        blocks, _ = await call_with_tools(
            model=model,
            system_prompt=_CRYSTALLIZE_SYSTEM,
            messages=[{"role": "user", "content": chain_text}],
            tools=[],
            temperature=0.0,
            max_tokens=1024,
        )
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        digest = _parse_llm_response(text, session_id)
    except Exception as e:
        logger.warning("crystallize_session LLM-Fehler für %s: %s — nutze Fallback", session_id, e)
        digest = _fallback_digest(session_id)

    # Deduplizierte files aus Observations + LLM-Ergebnis zusammenführen
    all_files: list[str] = list(digest["files_affected"])
    seen: set[str] = set(all_files)
    for obs in observations:
        for f in (obs.get("files") or []):
            if f not in seen:
                all_files.append(f)
                seen.add(f)

    crystal: Crystal = {
        "id": _generate_crystal_id(),
        "session_id": session_id,
        "agent_id": agent_id,
        "project": project,
        "created_at": _now_iso(),
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
