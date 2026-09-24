"""Conservative metadata-only evidence continuity for direct session resumes."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from hydrahive.db.connection import db
from hydrahive.runner.integrity_evidence import EVIDENCE_KINDS

_MAX_AGE = timedelta(hours=24)
_RESUME_WORDS = frozenset({
    "bitte", "continue", "dann", "der", "fortfahren", "go", "ja", "jetzt",
    "mach", "machen", "nach", "nun", "ok", "okay", "on", "please", "proceed",
    "reihe", "resume", "weiter", "weitermachen",
})
_RESUME_ACTIONS = frozenset({
    "continue", "fortfahren", "go", "proceed", "resume", "weiter", "weitermachen",
})
_FINISH_CURRENT = re.compile(
    r"^(?:(?:ok|okay) )?(?:machen wir|lass uns) (?:das|dies|alles)\b.{0,80}\bfertig\b"
)
_NEGATED_RESUME = re.compile(r"\b(?:abbrechen|cancel|nicht|stop|stopp|stoppen)\b")
_STATUS_PHRASES = frozenset({
    "auf welchem stand sind wir",
    "wie ist der aktuelle stand",
    "wie ist der aktuelle status",
    "was ist der aktuelle stand",
    "was ist der aktuelle status",
})


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-zäöüß]+", text.casefold()))


def is_direct_continuation(text: str) -> bool:
    """Accept only short, unambiguous resume/status utterances."""
    normalized = _normalize(text)
    if not normalized or len(normalized) > 120 or _NEGATED_RESUME.search(normalized):
        return False
    if _FINISH_CURRENT.match(normalized):
        return True
    words = normalized.split()
    status_words = words[1:] if words and words[0] in {"ok", "okay", "bitte"} else words
    if " ".join(status_words) in _STATUS_PHRASES:
        return True
    return bool(_RESUME_ACTIONS.intersection(words)) and all(
        word in _RESUME_WORDS for word in words
    )


def load_continuation_evidence(
    session_id: str, user_text: str, *, now: datetime | None = None,
) -> frozenset[str]:
    """Load bounded known evidence from the latest same-session snapshot."""
    if not is_direct_continuation(user_text):
        return frozenset()
    until = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    since = until - _MAX_AGE
    with db() as conn:
        row = conn.execute(
            """SELECT metadata FROM messages
               WHERE session_id = ? AND created_at >= ? AND created_at <= ?
                 AND metadata LIKE ?
               ORDER BY created_at DESC LIMIT 1""",
            (
                session_id,
                since.isoformat(timespec="milliseconds"),
                until.isoformat(timespec="milliseconds"),
                '%"integrity"%',
            ),
        ).fetchone()
    if not row:
        return frozenset()
    try:
        integrity = json.loads(row["metadata"] or "{}").get("integrity")
        snapshot = integrity.get("snapshot") if isinstance(integrity, dict) else None
        raw_evidence = snapshot.get("evidence_kinds") if isinstance(snapshot, dict) else None
    except (json.JSONDecodeError, TypeError):
        return frozenset()
    if not isinstance(raw_evidence, list):
        return frozenset()
    return frozenset(
        item for item in raw_evidence
        if isinstance(item, str) and item in EVIDENCE_KINDS
    )
