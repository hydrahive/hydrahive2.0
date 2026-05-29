"""Gist-Card: abgeleitete, recompute-safe Verdichtung einer Session. Vertrag für L2/L3."""
from __future__ import annotations

from dataclasses import dataclass, field

VALENCE = ("good", "bad", "neutral")
SALIENCE = ("high", "low")
GROUNDEDNESS = ("observed", "claimed", "mixed")
CARD_SCHEMA_VERSION = 1


@dataclass
class Card:
    card_id: str                 # "card:{session_id}"
    session_id: str
    gist: str
    valence: str                 # good|bad|neutral
    salience: str                # high|low
    groundedness: str            # observed|claimed|mixed (v1: aus Event-Typ-Mix)
    topics: list[str] = field(default_factory=list)
    agent_id: str | None = None
    agent_name: str | None = None
    username: str | None = None
    created_at: str | None = None        # Session-Zeit (ISO) → Recency
    source: dict | None = None           # {"session_id":..., "event_count":...}
    # embedding wird separat als pgvector-Spalte gehalten (Mirror-Dim, dynamisch)
    confidence: float = 1.0              # v2, ungenutzt in v1
    superseded_by: list[str] = field(default_factory=list)   # v2
    supersedes: list[str] = field(default_factory=list)      # v2
    schema_version: int = CARD_SCHEMA_VERSION
    computed_at: str | None = None
    consolidation_model: str | None = None


def derive_groundedness(tool_result_count: int, assistant_text_count: int) -> str:
    """v1-Heuristik: belegt vs Behauptung aus Event-Typ-Mix.
    tool_result = beobachtet/belegt, assistant_text = Behauptung."""
    obs, clm = tool_result_count, assistant_text_count
    if obs == 0 and clm == 0:
        return "mixed"
    if obs >= 2 * clm:
        return "observed"
    if clm >= 2 * obs:
        return "claimed"
    return "mixed"
