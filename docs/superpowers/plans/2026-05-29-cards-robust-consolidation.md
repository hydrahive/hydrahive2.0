# Robuste Card-Konsolidierung — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Karten-Konsolidierung gegen LLM-Output-Varianz härten, damit wertvolle Sessions nicht mehr lautlos mit leerem Gist landen.

**Architecture:** Rein **cards-lokaler** Fix (kein Eingriff in den geteilten LLM-Bridge). Drei Hebel: (1) smarte JSON-Extraktion zieht das *Card*-Objekt statt des ersten `{`; (2) Prompt-Rahmung + Claude-Assistant-Prefill zwingen das Modell zu verdichten statt fortzuführen; (3) Retry + kein lautloses Leer-Speichern macht Restfehler sichtbar und wiederholbar.

**Tech Stack:** Python 3.12, pytest, Anthropic-SDK (über bestehendes `call_with_tools`), kein neuer Dependency.

---

## Root Cause (empirisch belegt, `raw.log` 2026-05-29)

22 der 353 Sessions scheitern **deterministisch** (nicht transient: heal-Lauf 4/26). 0 LLM-Exceptions → der Call gelingt, die Antwort ist nur kein verwertbares Card-JSON. Drei Modi:

- **Mode 1** (`019e335d`, 925 ev): Modell antwortet konversationell („Alles klar! Ich habe die Infos…") — gar kein JSON.
- **Mode 2** (`2ecf6ba0`, 3014 ev): Modell baut die Card **korrekt**, stellt aber echoed Content voran (`[system_stop_hook_summary] {"parentUuid":…}`). `_extract_json_object` greift das **erste** `{` (Hook-Objekt, gültiges aber falsches JSON, kein `gist`) → leer.
- **Mode 3** (`019e73fe`, 1910 ev): Modell führt die Arbeit fort (Prosa + echoed Code) — kein Card-JSON; erstes `{` ist Zufalls-Content.

Gemeinsamer Kern: (A) Modell verdichtet nicht immer, sondern *führt fort/echoed*; (B) Extraktion nimmt das erste statt des richtigen Objekts. **Modellwechsel auf Sonnet ist kein Fix** (Sonnet fiel in dieser Session ebenfalls zurück); die Struktur ist das Problem.

## File Structure

- Modify: `core/src/hydrahive/cards/_consolidate_prompts.py` — smarte Extraktion (`_iter_json_objects`, `parse_card_response`), Prompt-Härtung (`CARD_SYSTEM`), Transkript-Rahmung (`card_user_message`).
- Modify: `core/src/hydrahive/cards/consolidate.py` — Claude-Prefill (`_is_claude`, `_llm_tags`), Retry + kein lautloses Leer-Speichern in `consolidate_session`.
- Test: `core/tests/test_consolidate.py` — erweitert (Fixtures aus `raw.log`).
- Test: `core/tests/test_cards_robustness.py` — neu (Extraktion-Modi, Prefill, Retry, no-silent-success).

---

### Task 0: Branch

- [ ] **Step 1: Branch anlegen**

```bash
cd /home/till/hydrahive2.0
git checkout main && git pull --ff-only
git checkout -b fix/cards-robust-consolidation
```

---

### Task 1: Smarte JSON-Extraktion (fixt Mode 2)

**Files:**
- Modify: `core/src/hydrahive/cards/_consolidate_prompts.py`
- Test: `core/tests/test_cards_robustness.py`

- [ ] **Step 1: Failing test schreiben**

```python
# core/tests/test_cards_robustness.py
from hydrahive.cards._consolidate_prompts import parse_card_response

# Mode 2 (raw.log): echoed Hook-JSON VOR der echten Card → Card hat gist-Key
MODE2 = (
    'Läuft jetzt?\n[system_stop_hook_summary] {"parentUuid": "a8c8", '
    '"hookInfos": [{"command": "x"}], "lastPrompt": "nein"}\n```\n\n```json\n'
    '{"gist": "Analyzed ATLAS_OS & UI-TARS; debugged bubbletea TUI raw-mode.", '
    '"valence": "good", "salience": "high", "topics": ["ATLAS_OS", "UI-TARS"]}\n```'
)

def test_extraction_skips_echoed_object_and_finds_card():
    out = parse_card_response(MODE2)
    assert out["gist"].startswith("Analyzed ATLAS_OS")
    assert out["valence"] == "good" and out["salience"] == "high"
    assert "ATLAS_OS" in out["topics"]
```

- [ ] **Step 2: Test laufen → FAIL**

Run: `cd /home/till/hydrahive2.0/core && python3.12 -m pytest tests/test_cards_robustness.py::test_extraction_skips_echoed_object_and_finds_card -v`
Expected: FAIL — `gist` ist leer (alte Logik greift das `{"parentUuid":…}`-Objekt).

- [ ] **Step 3: Implementieren**

Ersetze `_extract_json_object` durch einen Iterator + gist-bewusste Auswahl in `parse_card_response`:

```python
def _iter_json_objects(text: str):
    """Yield jedes balancierte top-level {...} (String-/Escape-aware)."""
    i, n = 0, len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = False
        esc = False
        for j in range(i, n):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    yield text[i:j + 1]
                    i = j + 1
                    break
        else:
            return  # unbalancierter Rest → Schluss


def parse_card_response(text: str) -> dict:
    """Robustes Parsing: wählt das JSON-Objekt MIT "gist"-Key (nicht das erste
    beliebige {…}) — toleriert echoed Content/Prosa/Fences davor."""
    best = None
    for raw in _iter_json_objects((text or "").strip()):
        try:
            p = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(p, dict) and "gist" in p:
            best = p
            break
        if best is None and isinstance(p, dict):
            best = p  # Fallback: erstes gültige Objekt, falls keines gist hat
    if not isinstance(best, dict) or "gist" not in best:
        logger.warning("parse_card_response: kein Card-JSON (gist-Key) gefunden — leere Tags (Fallback)")
        return {"gist": "", "valence": "neutral", "salience": "low", "topics": []}
    return {
        "gist": str(best.get("gist", ""))[:300],
        "valence": best.get("valence") if best.get("valence") in VALENCE else "neutral",
        "salience": best.get("salience") if best.get("salience") in SALIENCE else "low",
        "topics": [str(t)[:60] for t in (best.get("topics") or [])][:6],
    }
```

- [ ] **Step 4: Test + Regressions laufen → PASS**

Run: `cd /home/till/hydrahive2.0/core && python3.12 -m pytest tests/test_cards_robustness.py tests/test_consolidate.py -v`
Expected: PASS (inkl. der bestehenden `test_parse_card_*` — gleiches Verhalten für Single-Object/Fenced/nested-brace-in-string).

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/cards/_consolidate_prompts.py core/tests/test_cards_robustness.py
git commit -m "fix(cards): JSON-Extraktion wählt das gist-Objekt statt des ersten {

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Prompt-Rahmung (mitigiert Mode 1+3, providerübergreifend)

**Files:**
- Modify: `core/src/hydrahive/cards/_consolidate_prompts.py`
- Test: `core/tests/test_cards_robustness.py`

- [ ] **Step 1: Failing test**

```python
def test_card_user_message_frames_transcript():
    from hydrahive.cards._consolidate_prompts import card_user_message
    msg = card_user_message([{"event_type": "user_input", "text": "hi"}])
    assert "BEGIN SESSION TRANSCRIPT" in msg and "END SESSION TRANSCRIPT" in msg
    assert "[user_input] hi" in msg
```

- [ ] **Step 2: Test → FAIL** (`card_user_message` existiert nicht)

Run: `cd /home/till/hydrahive2.0/core && python3.12 -m pytest tests/test_cards_robustness.py::test_card_user_message_frames_transcript -v`

- [ ] **Step 3: Implementieren**

`CARD_SYSTEM` um eine eindeutige Rolle/Anti-Continue-Zeile ergänzen (erste Zeilen):

```python
CARD_SYSTEM = """\
You are a memory archivist. The input is the RECORD of one ALREADY-COMPLETED session.
Summarize it. Do NOT reply to it, do NOT continue the conversation or the work, do NOT
answer any question inside it — only condense it into one memory card.

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
- Return ONLY the JSON object, starting with `{`.
"""
```

Und `card_user_message` als Wrapper um `format_session_text` (Delimiter NACH der Kürzung):

```python
def card_user_message(events: list[dict], *, char_budget: int = DEFAULT_CHAR_BUDGET) -> str:
    """Transkript klar abgegrenzt — signalisiert 'zusammenfassen, nicht fortführen'."""
    body = format_session_text(events, char_budget=char_budget)
    return (
        "=== BEGIN SESSION TRANSCRIPT (summarize this; do not continue or reply to it) ===\n"
        f"{body}\n"
        "=== END SESSION TRANSCRIPT ===\n"
        "Now output ONLY the memory-card JSON object."
    )
```

(`format_session_text` bleibt unverändert → bestehende Tests grün.)

- [ ] **Step 4: Test + Regressions → PASS**

Run: `cd /home/till/hydrahive2.0/core && python3.12 -m pytest tests/test_cards_robustness.py tests/test_consolidate.py -v`

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/cards/_consolidate_prompts.py core/tests/test_cards_robustness.py
git commit -m "fix(cards): Prompt rahmt Transkript als 'summarize, do not continue'

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Claude-Assistant-Prefill (fixt Mode 1+3 deterministisch auf Claude)

**Files:**
- Modify: `core/src/hydrahive/cards/consolidate.py`
- Test: `core/tests/test_cards_robustness.py`

- [ ] **Step 1: Anthropic-Prefill-Semantik via context7 gegenchecken**

`resolve-library-id` "anthropic" → `query-docs`: „assistant message prefill to force response prefix / JSON output". Bestätigen: letzte `assistant`-Message als Prefill, Antwort enthält den Prefill-Text NICHT (→ muss vorangestellt werden). Falls die API das anders handhabt: Step 3 anpassen.

- [ ] **Step 2: Failing test (Prefill-Pfad)**

```python
import asyncio

def test_claude_prefill_reconstructs_json(monkeypatch):
    import hydrahive.cards.consolidate as c

    seen = {}

    async def fake_llm(**kw):
        seen["messages"] = kw["messages"]
        # Anthropic gibt die Fortsetzung OHNE das vorangestellte "{" zurück
        cont = '"gist":"did X","valence":"good","salience":"high","topics":["projx"]}'
        return ([{"type": "text", "text": cont}], "", {})

    monkeypatch.setattr("hydrahive.runner.llm_bridge.call_with_tools", fake_llm)
    tags = asyncio.run(c._llm_tags(
        [{"event_type": "user_input", "text": "hi"}], "claude-haiku-4-5"))

    assert tags["gist"] == "did X" and tags["valence"] == "good"
    assert seen["messages"][-1] == {"role": "assistant", "content": "{"}  # Prefill gesetzt
```

- [ ] **Step 3: Test → FAIL** (`_llm_tags` existiert nicht)

Run: `cd /home/till/hydrahive2.0/core && python3.12 -m pytest tests/test_cards_robustness.py::test_claude_prefill_reconstructs_json -v`

- [ ] **Step 4: Implementieren** (`consolidate.py`)

```python
def _is_claude(model: str) -> bool:
    from hydrahive.llm import client as llm_client
    return llm_client._strip_provider_prefix(model or "").startswith("claude-")


async def _llm_tags(events: list[dict], model: str) -> dict:
    """Ein LLM-Call → geparste Card-Tags. Claude: Assistant-Prefill '{' erzwingt
    JSON (verhindert Prosa/Fortführen). Bei Exception: leere Default-Tags."""
    from hydrahive.cards._consolidate_prompts import CARD_SYSTEM, card_user_message, parse_card_response
    from hydrahive.runner.llm_bridge import call_with_tools

    messages: list[dict] = [{"role": "user", "content": card_user_message(events)}]
    prefill = _is_claude(model)
    if prefill:
        messages.append({"role": "assistant", "content": "{"})
    try:
        blocks, _, _ = await call_with_tools(
            model=model, system_prompt=CARD_SYSTEM, messages=messages,
            tools=[], temperature=0.0, max_tokens=512,
        )
    except Exception as e:
        logger.warning("consolidate: LLM-Fehler %s — leere Tags", e)
        return {"gist": "", "valence": "neutral", "salience": "low", "topics": []}
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    if prefill:
        text = "{" + text
    return parse_card_response(text)
```

- [ ] **Step 5: Test + Regressions → PASS**

Run: `cd /home/till/hydrahive2.0/core && python3.12 -m pytest tests/test_cards_robustness.py tests/test_consolidate.py -v`
Expected: PASS (bestehender `test_consolidate_session_builds_card` nutzt Modell `"test-model"` → kein Prefill → unverändert).

- [ ] **Step 6: Commit**

```bash
git add core/src/hydrahive/cards/consolidate.py core/tests/test_cards_robustness.py
git commit -m "fix(cards): Claude-Assistant-Prefill erzwingt JSON-Output (Mode 1+3)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Retry + kein lautloses Leer-Speichern

**Files:**
- Modify: `core/src/hydrahive/cards/consolidate.py`
- Test: `core/tests/test_cards_robustness.py`

- [ ] **Step 1: Failing tests**

```python
def test_retry_then_success(monkeypatch):
    import hydrahive.cards.consolidate as c
    calls = {"n": 0}

    async def fake_detail(sid):
        return {"session": {}, "events": [{"event_type": "user_input", "text": "hi"}]}
    async def fake_counts(sid):
        return {"tool_result": 0, "assistant_text": 1}
    captured = {}
    async def fake_upsert(card, embedding=None):
        captured["card"] = card
    async def fake_llm(**kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return ([{"type": "text", "text": "Alles klar!"}], "", {})  # Mode-1-Prosa
        return ([{"type": "text", "text": '{"gist":"ok","valence":"good","salience":"low","topics":[]}'}], "", {})

    monkeypatch.setattr(c, "get_session_detail", fake_detail)
    monkeypatch.setattr(c, "event_type_counts", fake_counts)
    monkeypatch.setattr(c, "upsert_card", fake_upsert)
    monkeypatch.setattr("hydrahive.runner.llm_bridge.call_with_tools", fake_llm)
    monkeypatch.setattr("hydrahive.llm._config.load_config", lambda: {"embed_model": ""})

    card = asyncio.run(c.consolidate_session("s1", "x-model"))
    assert calls["n"] == 2 and card is not None and card.gist == "ok"


def test_persistent_empty_returns_none_and_no_upsert(monkeypatch):
    import hydrahive.cards.consolidate as c
    async def fake_detail(sid):
        return {"session": {}, "events": [{"event_type": "user_input", "text": "hi"}]}
    upserts = {"n": 0}
    async def fake_upsert(card, embedding=None):
        upserts["n"] += 1
    async def fake_llm(**kw):
        return ([{"type": "text", "text": "Alles klar, ich antworte nur Prosa."}], "", {})

    monkeypatch.setattr(c, "get_session_detail", fake_detail)
    monkeypatch.setattr(c, "upsert_card", fake_upsert)
    monkeypatch.setattr("hydrahive.runner.llm_bridge.call_with_tools", fake_llm)

    card = asyncio.run(c.consolidate_session("s1", "x-model"))
    assert card is None and upserts["n"] == 0  # nichts Leeres gespeichert
```

- [ ] **Step 2: Tests → FAIL**

Run: `cd /home/till/hydrahive2.0/core && python3.12 -m pytest tests/test_cards_robustness.py -k "retry or persistent" -v`

- [ ] **Step 3: Implementieren** — `consolidate_session` umbauen (Tags via `_llm_tags`, Retry, früher Abbruch):

```python
async def consolidate_session(session_id: str, model: str) -> Card | None:
    """Eine Mirror-Session → eine Card (idempotent via upsert_card).
    None, wenn Session fehlt ODER nach Retry kein Gist erzeugbar (retry-fähig,
    nicht lautlos leer speichern)."""
    detail = await get_session_detail(session_id)
    if not detail:
        return None
    meta = detail.get("session") or {}
    events = detail.get("events") or []

    tags = await _llm_tags(events, model)
    if not tags["gist"]:
        tags = await _llm_tags(events, model)  # ein Retry gegen Varianz
    if not tags["gist"]:
        logger.warning(
            "consolidate_session %s: kein Gist nach Retry — Card NICHT gespeichert (retry-fähig)",
            session_id,
        )
        return None

    counts = await event_type_counts(session_id)
    groundedness = derive_groundedness(
        counts.get("tool_result", 0), counts.get("assistant_text", 0)
    )

    embedding = None
    from hydrahive.llm._config import load_config
    from hydrahive.llm.embed import aembed
    embed_model = load_config().get("embed_model", "")
    if embed_model:
        try:
            embedding = await aembed(tags["gist"], embed_model, embed_type="db")
        except Exception as e:
            logger.warning("consolidate_session %s: Embedding-Fehler %s", session_id, e)

    created_at = meta.get("started_at")
    card = Card(
        card_id=f"card:{session_id}",
        session_id=session_id,
        gist=tags["gist"],
        valence=tags["valence"],
        salience=tags["salience"],
        groundedness=groundedness,
        topics=tags["topics"],
        agent_id=meta.get("agent_id"),
        agent_name=meta.get("agent_name"),
        username=meta.get("username"),
        created_at=str(created_at) if created_at is not None else None,
        source={"session_id": session_id, "event_count": len(events)},
        consolidation_model=model,
    )
    await upsert_card(card, embedding)
    logger.info(
        "consolidate_session %s: Card (valence=%s salience=%s grounded=%s, %d events)",
        session_id, card.valence, card.salience, card.groundedness, len(events),
    )
    return card
```

Den alten Inline-LLM-Block (CARD_SYSTEM/format_session_text/call_with_tools/parse_card_response + try/except) **entfernen** — ersetzt durch `_llm_tags`. Ungenutzte Imports (`CARD_SYSTEM`, `format_session_text`, `parse_card_response`) aus dem Modulkopf von `consolidate.py` entfernen.

- [ ] **Step 4: Tests → PASS**

Run: `cd /home/till/hydrahive2.0/core && python3.12 -m pytest tests/test_cards_robustness.py tests/test_consolidate.py -v`

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/cards/consolidate.py core/tests/test_cards_robustness.py
git commit -m "fix(cards): Retry + leere Card nicht lautlos als fertig speichern

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Volle Suite, Merge, Deploy, Heilung messen

- [ ] **Step 1: Volle Core-Suite grün**

Run: `cd /home/till/hydrahive2.0/core && python3.12 -m pytest -q`
Expected: alles grün (Baseline war 575+).

- [ ] **Step 2: Review durch Till** — Diff `git diff main...fix/cards-robust-consolidation` vorlegen. Erst nach OK weiter.

- [ ] **Step 3: Merge nach main** (kein PR — gleiches Konto):

```bash
git checkout main && git merge --no-ff fix/cards-robust-consolidation
git push origin main
```

- [ ] **Step 4: Deploy `.22`** — Till klickt Update (oder `sudo touch /var/lib/hydrahive2/.update_request`). HEAD == neuer Commit verifizieren via MCP `hh_status`.

- [ ] **Step 5: Die 22 Leeren nachfahren + messen** — `heal_empties.py` (Haiku) erneut laufen (Service-Env-Wrapper). Erwartung: deutlich mehr als 4/26 geheilt; Restfehler werden jetzt **geloggt**, nicht lautlos. Tabelle: `embedding`-Count steigt Richtung Gesamtzahl.

- [ ] **Step 6: Entscheidung Forced-Tools?** — bleibt ein harter Rest (sollte mit Prefill ~0 sein), erst dann separat Forced-Tool-Output am Bridge gaten. Sonst: erledigt.

---

## Self-Review

- **Spec-Coverage:** Mode 1 → Prefill+Prompt (T2,T3) + Retry/no-silent (T4). Mode 2 → Extraktion (T1). Mode 3 → Prefill+Prompt (T2,T3). Silent-failure → T4. ✓
- **Placeholder-Scan:** keine TODO/„handle errors" — alle Steps mit konkretem Code/Command. ✓
- **Typ-Konsistenz:** `_llm_tags(events, model) -> dict` (T3) wird in `consolidate_session` (T4) genutzt; `card_user_message` (T2) in `_llm_tags` (T3); `parse_card_response`-Rückgabe-Shape unverändert (gist/valence/salience/topics). ✓
- **Risiko:** kein Eingriff in geteilten LLM-Bridge; Prefill auf `claude-*` gegated (no-op für NIM/.23); `format_session_text` unverändert (Alt-Tests grün).
