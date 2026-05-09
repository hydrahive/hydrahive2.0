"""Crystallize-Pipeline — LLM-Prompt, Chain-Text, Response-Parsing, Fallbacks."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


CRYSTALLIZE_SYSTEM = """\
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


def fingerprint(text: str) -> str:
    """SHA256[:12] des Textes — stabiler Key für Lesson-Dedup."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def generate_crystal_id() -> str:
    ts = int(time.time() * 1000)
    rand = secrets.token_hex(4)
    return f"crys_{ts}_{rand}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_llm_response(text: str, session_id: str) -> dict[str, Any]:
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
        return fallback_digest(session_id)

    return {
        "narrative": str(parsed.get("narrative", ""))[:200],
        "key_outcomes": [str(o) for o in parsed.get("key_outcomes", [])[:8]],
        "files_affected": [str(f) for f in parsed.get("files_affected", [])],
        "lessons": [str(l) for l in parsed.get("lessons", [])[:5]],
    }


def fallback_digest(session_id: str) -> dict[str, Any]:
    """Minimaler Fallback wenn LLM-Parsing fehlschlägt."""
    return {
        "narrative": f"Session {session_id} abgeschlossen.",
        "key_outcomes": [],
        "files_affected": [],
        "lessons": [],
    }
