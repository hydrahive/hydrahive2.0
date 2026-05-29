"""Card-Consolidation — Prompt, Event-Formatierung (mit Truncation), Parsing.

Reine Funktionen (lokal/ohne PG testbar). Quelle ist der Datamining-Mirror
(`get_session_detail`), NICHT `crystallize_session` (agent-lokal → None für
externe/importierte Sessions). crystallize wird nur als Prompt-*Muster*
wiederverwendet.
"""
from __future__ import annotations

import json
import logging

from hydrahive.db._mirror_cards_model import SALIENCE, VALENCE

logger = logging.getLogger(__name__)

# Char-Budget für den LLM-Input. Große Sessions (tausende Events) werden auf
# head+tail gekürzt — die Card ist ein Gist; source.event_count +
# datamining_search erlauben tieferes Graben (kein Informationsverlust im Store).
DEFAULT_CHAR_BUDGET = 24000

CARD_SYSTEM = """\
You are condensing one session of agent/user activity into a compact memory card.
The input is the session's event log (user inputs, assistant text, tool calls/results).

Respond with valid JSON only — no markdown, no explanation:
{
  "gist": "<1-3 lines: the essence of this session>",
  "valence": "good | bad | neutral",
  "salience": "high | low",
  "topics": ["<short topic/entity>", "..."]
}

Rules:
- gist: concise, factual, max 300 chars — what happened / was decided / built.
- valence: good = went well/succeeded; bad = failed/blocked/error; neutral otherwise.
- salience: high = decision/error/feedback/notable; low = routine.
- topics: max 6 short cue words (projects, entities, components) for later retrieval.
- Return ONLY the JSON object.
"""


def format_session_text(events: list[dict], *, char_budget: int = DEFAULT_CHAR_BUDGET) -> str:
    """Mirror-Events (aus get_session_detail) → lesbarer LLM-Input, gekürzt auf
    head+tail wenn über char_budget (große Sessions, z.B. 9k+ Events)."""
    if not events:
        return "(no events)"
    lines: list[str] = []
    for e in events:
        et = e.get("event_type", "other")
        head = f"[{et}:{e['tool_name']}]" if e.get("tool_name") else f"[{et}]"
        body = (e.get("text") or e.get("tool_output") or "").strip()
        lines.append(f"{head} {body}" if body else head)
    text = "\n".join(lines)
    if len(text) <= char_budget:
        return text
    head_n = int(char_budget * 0.6)
    tail_n = char_budget - head_n
    elided = len(text) - char_budget
    return text[:head_n] + f"\n…[{elided} chars elided]…\n" + text[-tail_n:]


def parse_card_response(text: str) -> dict:
    """Robustes JSON-Parsing der LLM-Antwort → validierte Tags. Fallback bei Murks."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = "\n".join(
            ln for ln in text.splitlines() if not ln.strip().startswith("```")
        ).strip()
    try:
        p = json.loads(text)
        if not isinstance(p, dict):
            raise ValueError("not an object")
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("parse_card_response: ungültiges JSON — leere Tags (Fallback)")
        return {"gist": "", "valence": "neutral", "salience": "low", "topics": []}
    return {
        "gist": str(p.get("gist", ""))[:300],
        "valence": p.get("valence") if p.get("valence") in VALENCE else "neutral",
        "salience": p.get("salience") if p.get("salience") in SALIENCE else "low",
        "topics": [str(t)[:60] for t in (p.get("topics") or [])][:6],
    }
