# Proaktiver Recall (v1) — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development oder superpowers:executing-plans. Steps mit Checkbox (`- [ ]`).

**Goal:** v1 aus der SPEC (`SPEC.md` „Proaktiver Recall", `56aaa82`) bauen: Sessions werden offline zu getaggten Gist-Cards verdichtet und billig in den Agenten-Kontext gewebt (A gecacht + C cue-getriggert). Kein Contradiction-Reasoning / Verify-Gate (= v2).

**Architecture:** Card-Store als neue PG-Tabelle im Mirror (recompute-safe, getrennt vom kuratierten Memory). Konsolidierung baut auf `tools/_crystallize.py` (Crystal = gist-Basis) + der Zahnfee-Batch-Maschinerie. Recall über `runner/system_prompt.py` (Weaving) + `db/_mirror_search.py` (pgvector). Tags: gist/valence/salience/topics vom LLM, groundedness aus Event-Typ-Mix abgeleitet.

**Tech Stack:** Python 3.12 / asyncpg / pgvector / pytest. Keine neuen Deps.

**Aufteilung (Joshuas Regie):** schmied = Card-Schema-Vertrag + Capture-Ende (Groundedness-Ableitung, Per-Session-Event-Provenance). joshua = L2/L3-Hirn (Card-Writer, Card-Store-Writes, Recall A+C). **Card-Schema-Vertrag (Task 1) zuerst** → dann parallel über Feature-Branches + gegenseitige PR-Reviews. Joshuas Tasks sind hier als **Vertrag + Akzeptanz-Test + Build-on** spezifiziert; die internen Bau-Schritte macht joshua.

**Deployment/Test:** PG-abhängige Teile testet Till nach Deploy (kein lokaler Mirror, kein Prod-Zugriff durch Claude). Reine Funktionen sind lokal TDD-bar.

---

## File Structure

- Create: `core/src/hydrahive/db/_mirror_cards.py` — Card-Store: DDL, upsert, list (recency×salience), pgvector-Suche. *(joshua)*
- Modify: `core/src/hydrahive/db/_mirror_ddl.py` — `cards`-Tabelle + Embedding-Spalte/Index ins DDL-Pattern. *(joshua)*
- Create: `core/src/hydrahive/db/_mirror_cards_model.py` — Card-Dataclass + `derive_groundedness()` (rein). *(schmied — der Vertrag)*
- Create: `core/src/hydrahive/cards/consolidate.py` — Card-Writer: Session → crystallize → Tags → Embedding → upsert. *(joshua)*
- Modify: `core/src/hydrahive/zahnfee/scheduler.py` (oder neuer Batch) — Konsolidierungs-Lauf takten. *(joshua)*
- Modify: `core/src/hydrahive/runner/system_prompt.py` — Recall A (Cards in den Stabil-Prompt) + C (cue-getriggert). *(joshua)*
- Tests: `core/tests/test_card_groundedness.py` *(schmied)*, `core/tests/test_mirror_cards.py` / `test_consolidate.py` / `test_recall_weaving.py` *(joshua)*

---

## Task 1: Card-Schema-Vertrag (zuerst — entsperrt paralleles Bauen) · *schmied*

**Files:**
- Create: `core/src/hydrahive/db/_mirror_cards_model.py`
- Test: `core/tests/test_card_groundedness.py`

Der Vertrag, gegen den beide bauen. Card-Felder (v1 gefüllt; v2-Felder vorhanden, ungenutzt):

```python
# core/src/hydrahive/db/_mirror_cards_model.py
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
```

- [ ] **Step 1: Failing-Test schreiben**

```python
# core/tests/test_card_groundedness.py
from hydrahive.db._mirror_cards_model import derive_groundedness, Card, CARD_SCHEMA_VERSION


def test_observed_when_tool_results_dominate():
    assert derive_groundedness(tool_result_count=10, assistant_text_count=2) == "observed"


def test_claimed_when_assistant_text_dominates():
    assert derive_groundedness(tool_result_count=1, assistant_text_count=10) == "claimed"


def test_mixed_when_balanced():
    assert derive_groundedness(tool_result_count=5, assistant_text_count=4) == "mixed"


def test_empty_session_is_mixed():
    assert derive_groundedness(0, 0) == "mixed"


def test_card_defaults_v2_fields_unused():
    c = Card(card_id="card:s1", session_id="s1", gist="g", valence="good",
             salience="high", groundedness="observed")
    assert c.confidence == 1.0 and c.superseded_by == [] and c.schema_version == CARD_SCHEMA_VERSION
```

- [ ] **Step 2: Fehlschlag bestätigen**

Run: `cd core && python3 -m pytest tests/test_card_groundedness.py -v`
Expected: FAIL — `ModuleNotFoundError: hydrahive.db._mirror_cards_model`

- [ ] **Step 3: `_mirror_cards_model.py` schreiben** (Code oben).

- [ ] **Step 4: PASS bestätigen**

Run: `cd core && python3 -m pytest tests/test_card_groundedness.py -v`
Expected: PASS (5 Tests)

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/db/_mirror_cards_model.py core/tests/test_card_groundedness.py
git commit -m "feat(cards): Card-Schema-Vertrag + derive_groundedness (v1-Heuristik)"
```

---

## Task 2: Per-Session-Event-Typ-Counts (Groundedness-Input) · *schmied*

**Files:**
- Create/Modify: `core/src/hydrahive/db/_mirror_cards.py` (Query-Teil; Store-Teil = Task 3/joshua)
- Test: integration (PG nötig) → Till nach Deploy; lokal nur Signatur-Smoke

Eine PG-Query, die pro Session die Event-Typ-Counts liefert, damit der Card-Writer `derive_groundedness` füttern kann.

```python
# in core/src/hydrahive/db/_mirror_cards.py
async def event_type_counts(pool, session_id: str) -> dict[str, int]:
    """{event_type: count} für eine Session — Input für derive_groundedness."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT event_type, COUNT(*)::int AS n FROM events WHERE session_id = $1 GROUP BY event_type",
            session_id,
        )
    return {r["event_type"]: r["n"] for r in rows}
```

- [ ] **Step 1:** Funktion schreiben (oben).
- [ ] **Step 2: Signatur-Smoke (kein PG)** — `cd core && python3 -c "from hydrahive.db import _mirror_cards"` → import ok.
- [ ] **Step 3: Commit** — `git commit -m "feat(cards): event_type_counts pro Session (Groundedness-Input)"`
- [ ] **Step 4 (Till, nach Deploy):** gegen echten Mirror prüfen: `event_type_counts(pool, "<session>")` liefert die Counts; `derive_groundedness(counts.get("tool_result",0), counts.get("assistant_text",0))` plausibel.

---

## Task 3: Card-Store + DDL · *joshua* (Vertrag + Akzeptanz; Bau-Schritte joshua)

**Files:** `db/_mirror_cards.py` (Store), `db/_mirror_ddl.py` (cards-Tabelle + Embedding-Spalte/Index — Pattern wie `ensure_embed_col`, **dynamische Mirror-Dim**, HNSW `vector_cosine_ops`).

**Vertrag (Signaturen):**
```python
async def ensure_cards_table(conn) -> None: ...           # CREATE TABLE IF NOT EXISTS cards (...) + Embedding-Spalte (Mirror-Dim) + HNSW-Index
async def upsert_card(pool, card: Card, embedding: list[float] | None) -> None: ...  # ON CONFLICT(card_id) DO UPDATE — recompute-safe
async def get_card(pool, card_id: str) -> dict | None: ...
async def wipe_cards(pool) -> int: ...                     # für wipe-and-rebuild
```
**Akzeptanz:** `cards`-Tabelle hat PK `card_id`, Embedding-Spalte in **Mirror-Dim** (gleiche wie `events.embedding`, via `ensure_embed_col`-Dim-Quelle), getrennt vom kuratierten Memory. `upsert_card` ist idempotent (zweimal dieselbe card_id → eine Zeile, aktualisiert). `wipe_cards` + Re-Konsolidierung ergibt identische Karten (recompute-safe). Keine Berührung der Memory-v2-Tabellen.

---

## Task 4: Card-Writer (Konsolidierung) · *joshua*

**Files:** `cards/consolidate.py`, Takt in `zahnfee/scheduler.py`.

**Vertrag:**
```python
async def consolidate_session(session_id: str, model: str | None) -> Card | None: ...  # _pool() intern (Modul-Konvention)
async def consolidate_recent(lookback_hours: int, model: str) -> int: ...               # Batch über MIRROR-Sessions, return Anzahl Karten
```
**Quelle = MIRROR (KORREKTUR — joshuas Task-4-Befund, verifiziert):** `consolidate_session` liest die Session-Events aus dem **Mirror** (`db/_mirror_sessions.get_session_detail`) und füttert sie in einen Verdichtungs-LLM-Call, der die **crystallize-Maschinerie wiederverwendet** (`runner.llm_bridge.call_with_tools` + Card-Prompt + `_crystallize_prompts`-Parse) — **NICHT** `crystallize_session` selbst. Grund: `crystallize_session` liest agent-lokale CompressedObservations (`settings.agents_dir/<id>/compressed/<sid>.jsonl`, `_compress_storage.py:16`) und gibt `None` zurück, wenn keine da sind → für die meisten Mirror-Sessions (joshua22/schmied/Importe) gäbe es keine Card. A ist SPEC-konsistent (Voraussetzungen: „Mirror = Quelle der Konsolidierung").
**Build-on (Tags):** `db/_mirror_sessions.event_type_counts` + `_mirror_cards_model.derive_groundedness` (Task 1/2) für `groundedness`; valence/salience/topics vom selben billigen LLM; Embedding über die Mirror-Embedding-Pipeline. **Große Sessions** (7–8k Events) → Events chunken (joshuas geflaggte Sorge, hier scharf).
**Akzeptanz:** Fixe Event-Fixtures → erwartete Tags (valence∈VALENCE, salience∈SALIENCE, groundedness aus Counts). Idempotenz: `consolidate_session` zweimal → eine Karte (via `upsert_card`). Billiges Modell, **kein** Widerspruchs-Reasoning (v2).

---

## Task 5: Recall A — gecachter Grundstock · *joshua*

**Files:** `runner/system_prompt.py` (im stabilen, gecachten Teil — siehe `_inject_longterm_memory`, `_stable_section`).

**Vertrag:**
```python
async def top_cards_for(pool, agent_id: str, project_id: str | None, n: int) -> list[Card]: ...  # Sortierung recency × salience
def render_cards_block(cards: list[Card]) -> str: ...   # kompakter Gist-Block für den Prompt
```
**Akzeptanz:** beim Session-Start landen ≤ N Karten (nach `recency × salience`) im **stabilen (gecachten)** System-Block (nicht im volatilen — sonst Cache-Bruch). Karten klar als „abgeleitete Erinnerungen" gelabelt, getrennt vom kuratierten Memory. Token-Test: Block unter definiertem Cap (z.B. ≤ N × ~1 Zeile).

---

## Task 6: Recall C — cue-getriggert · *joshua*

**Files:** `runner/system_prompt.py` bzw. Recall-Pfad + `db/_mirror_cards.py` (Suche).

**Vertrag:**
```python
async def search_cards(pool, query: str, limit: int) -> list[Card]: ...   # pgvector-Cosine über cards.embedding
```
**Build-on:** dasselbe Muster wie `db/_mirror_search.py:_semantic_search` (pgvector `<=>`), nur über `cards.embedding` statt `events.embedding`.
**Akzeptanz:** bei einem Cue (Projekt/Entität im Input) liefert `search_cards` thematisch passende Karten; injiziert als kleiner Block; Karten tragen `source` → Agent kann via `datamining_search` (`_mirror_search.search_events`) tiefer graben. **Nicht** jede Runde — nur bei Cue (sonst Token-Brand).

---

## Integration & Build-Order

1. **Task 1 (Card-Schema-Vertrag, schmied)** zuerst — entsperrt alles.
2. Parallel: **Task 2 (schmied, Groundedness-Query)** und **Task 3 (joshua, Card-Store/DDL)**.
3. **Task 4 (joshua, Card-Writer)** — braucht 1+2+3.
4. **Task 5 + 6 (joshua, Recall A+C)** — brauchen 3 (Store) + Karten (4).
5. Feature-Branches, gegenseitige PR-Reviews. Voraussetzung produktiv: Mirror + Embedding/pgvector aktiv.

## Governance

SPEC ✓ (`56aaa82`). Bau erst jetzt. v2 (Contradiction-Reasoning, Verify-Gate, Modell-Eskalation) bleibt **separat gegatet** unter Nicht-Zielen — kein Reinrutschen. Till testet die PG-Teile nach Deploy.

## Self-Review

**Spec-Coverage:** Konsolidierung→Card mit gist/valence/salience/groundedness/topics/source/embedding (Task 1+4) ✓; Derived recompute-safe Store getrennt vom Memory (Task 3) ✓; Recall A gecacht (Task 5) ✓; C cue-getriggert pgvector (Task 6) ✓; groundedness aus Event-Typ (Task 1+2) ✓. Nicht-Ziele (kein Reasoning/Verify/Eskalation/Blind-Suche) eingehalten — nirgends ein v2-Schritt.

**Platzhalter:** keine in den schmied-Tasks (voller Code). joshua-Tasks bewusst auf Vertrag+Akzeptanz+Build-on (seine technische Regie) — keine „TODO", sondern Signaturen + Akzeptanz-Tests als Vertrag.

**Typ-Konsistenz:** `Card`-Felder + `derive_groundedness`-Signatur (Task 1) == Nutzung in Task 2/4. `upsert_card`/`search_cards`/`top_cards_for` konsistent über Tasks 3/5/6. Embedding überall „Mirror-Dim, dynamisch" (kein hartes 4096).
