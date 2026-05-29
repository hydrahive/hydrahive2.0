# Proaktiver Recall — Design (v1 minimal + v2 erweitert)

**Status:** Design-Doc (Arbeitsartefakt). Verbindlich wird das Feature erst durch Tills SPEC-OK (standalone-Commit) + Plan. Nichts wird vor dem SPEC-OK gebaut.

**Datum:** 2026-05-29 · **Autoren:** schmied (Design, Capture-Ende) + joshua (technische Richtung L2/L3, Review)

---

## Nordstern: der „grüne Elefant" (Tills kognitives Modell)

Gedächtnis ist nicht *speichern + abrufen*, sondern **capture → konsolidieren MIT Denken → mit Verifikation abrufen** — wie ein Mensch:
- Tagsüber lernt man **unbewusst** (alles landet roh im Kurzzeit).
- Nachts **konsolidiert** das Hirn grob, sortiert gut/schlecht („chaotische Lagerhaltung").
- Im **Review** wird gegen Bestand geprüft („grün? Elefanten sind grau → muss ein Traum sein → als Traum taggen"), bei wackeligem Fundament **extern verifiziert** („hab ich je einen echten Elefanten gesehen? → googeln").
- Beim **Abruf** kommt die geprüfte Essenz, nicht das Rohprotokoll — und Ungeprüftes wird *nicht blind geglaubt*.

Die Linchpin: **eine erinnerte Sache kann selbst eine alte Halluzination sein.** Confidence/Groundedness-Tag + Verify-Gate = der Unterschied zwischen „KI erinnert sich falsch und handelt" und „erinnert sich, zweifelt richtig, prüft, handelt". Das unterscheidet ein selbstgehostetes Gedächtnis von einem Chat-Archiv.

## Token-Prinzip (der Grund, warum das Modell gewählt wurde)

Das **teure Denken passiert offline im „Schlaf"** (Batch, billiges Modell, einmal). Der **Recall ist tagsüber fast gratis** — er holt nur fertige, getaggte Karten:
- **A — gecachter Grundstock:** beim Session-Start Top-N Karten in den **stabilen (gecachten)** System-Prompt → ab Turn 2 Cache-Read, ~gratis.
- **C — cue-getriggert:** nur wenn ein Stichwort (Projekt/Entität) auftaucht, per pgvector verwandte Karten nachladen — selten.
- **Nie** blinde Suche pro Turn (das wäre „Tokens verbrennen").

---

## Architektur — 3 Schichten, auf Vorhandenem (kein Greenfield)

| Schicht | Aufgabe | Existierender Keim |
|---|---|---|
| **L1 Capture** | Roh-Events spiegeln (unbewusst) | Hook → Datamining (`db/mirror.py`) ✓ steht |
| **L2 Konsolidierung** | Roh → getaggte Gist-Cards (Schlaf-Batch) | **Crystallize** (`tools/_crystallize.py`: Session→Crystal+Lessons) + **Zahnfee** (`zahnfee/runner.py`: Offline-Batch, datamining→LLM→gespeichert) + **Memory-v2-Primitive** (`tools/write_memory.py`: confidence/reinforcements/superseded) |
| **L3 Recall** | Karten billig in den Kontext weben | Prompt-Weaving (`runner/system_prompt.py:_inject_longterm_memory`) + pgvector (`db/mirror_query.search_events`) |

**Leitsatz:** L2 = das vorhandene Crystallize **automatisieren + taggen + recompute-safe ablegen**, nicht neu bauen. L3 = die vorhandene Weaving-Maschinerie nutzen, nicht duplizieren.

---

## Das Card-Schema (DER Vertrag — zuerst, damit parallel gebaut werden kann)

Gist-Cards sind eine **abgeleitete, versionierte, recompute-safe** Schicht über dem immutablen Datamining. Jederzeit `wipe-and-rebuild` aus den Roh-Events — **getrennt** vom kuratierten Memory-v2, damit Neu-Rechnen die handgeschriebenen Agent-Notizen nicht mitreißt.

```jsonc
{
  "card_id": "card:{session_id}",      // stabil, aus session_id abgeleitet
  "session_id": "019e...",             // Anker im immutablen Datamining
  "agent_id": "b86014d5-...",
  "agent_name": "schmied",
  "username": "schmied",
  "created_at": "2026-05-29T...",       // Session-Zeit → Recency-Ranking

  // --- v1: vom Schlaf-Batch gefüllt ---
  "gist": "1–3 Zeilen Kern der Session",
  "valence": "good | bad | neutral",    // lief / scheiterte / neutral (LLM)
  "salience": "high | low",             // Entscheidung/Fehler/Feedback vs Routine (LLM)
  "groundedness": "observed | claimed | mixed",  // v1: aus Event-Typ-Mix ABGELEITET (Heuristik)
  "topics": ["projektx", "datamining-ingest"],   // Cues für C-Trigger
  "source": { "session_id": "019e...", "event_count": 777 },  // für lazy reconstruction

  // --- abgeleitete Recall-Hilfe ---
  "embedding": "vector(4096)",          // pgvector, Reuse der Mirror-Embedding-Pipeline

  // --- v2-ready (in v1 vorhanden aber UNGENUTZT) ---
  "confidence": 1.0,                    // v2: verify-before-trust
  "supersedes": [], "superseded_by": [],// v2: Widerspruchs-Reconcile (reuse Memory-v2 superseded)

  // --- recompute-safety ---
  "schema_version": 1,
  "computed_at": "2026-05-29T...",      // wann diese Ableitung lief
  "consolidation_model": "..."          // welches Modell die Karte schrieb
}
```

**`groundedness`-Heuristik (v1, billig):** Verhältnis `tool_result` zu `assistant_text` in der Session → überwiegend tool_result = `observed` (belegt), überwiegend assistant_text = `claimed` (Behauptung), gemischt = `mixed`. Frei aus der Event-Provenance, die wir eh spiegeln — **kein echtes Reasoning** (das ist v2).

---

## v1 (minimal) — Scope, hart abgegrenzt

**Drin:**
1. **L2 Schlaf-Batch:** automatisiert (Zahnfee-getaktet, nicht manuell) iteriert die Sessions, schreibt pro Session eine Gist-Card via Crystallize-LLM + die v1-Tags (gist/valence/salience/groundedness-Heuristik/topics/embedding). Billiges Modell, kein Eskalieren.
2. **Derived Card-Store:** eigener, recompute-safe Store; reuse der Memory-v2-Primitive (`confidence`/`superseded`-Felder vorhanden, ungenutzt) + der pgvector/Embedding-Pipeline — **nicht** neu bauen.
3. **L3 Recall A+C:** A = Top-N nach `recency × salience` in den gecachten Stabil-Prompt beim Start. C = cue-getriggert per pgvector. Karten tragen `source` → Agent gräbt bei Bedarf via `datamining_search`.

**Explizit DRAUSSEN (= v1 macht das NICHT):**
- Kein Contradiction-Reasoning / Umklassifizieren. `groundedness` ist nur die Event-Typ-Heuristik.
- Kein Verify-before-trust-Gate.
- Keine Modell-Eskalation.

> Der v1/v2-Schnitt **ist die Scope-Bremse.** Dieses Projekt hat die Trauma-Regel „keine unkontrollierte Feature-Entwicklung" (CLAUDE.md). v1 klein, v2 als separat gegatete Phase — kein Reinrutschen.

## v2 (erweitert) — eigener, später gegateter Task

- **Reviewer statt Zusammenfasser:** Widerspruchs-Abgleich gegen Bestand (Memory-v2 `superseded` + pgvector findet, wogegen geprüft wird), echte Groundedness (über die Heuristik hinaus), Umklassifizieren bei Evidenz (re-tag, wie „googeln").
- **Verify-before-trust-Gate:** Karten mit niedriger Confidence/Groundedness werden beim Recall *markiert* → Agent verifiziert (tiefer graben / extern), bevor er handelt.
- **Gestuftes Modell:** billig für die Masse (gist+valence), eskalieren auf ein stärkeres nur bei Widerspruch/niedriger Groundedness (joshuas #2 — ein zu dummer Reviewer vertaggt real↔Traum falsch).

---

## Offene Punkte — VOR dem Bau zu klären

1. **Source-Filter im Recall (joshuas #3, real):** `search_memory`/`load_filtered` filtert nach `project`, ein expliziter `source`-Filter (kuratiert vs. auto) ist nicht erkennbar. Entweder *ein* Store-Backend mit `source`-Feld + zwei Sichten, oder getrennte Retrieval-Pfade fürs Weben beider Stores. Empfehlung: **getrennter Card-Store mit eigenem Retrieval** (recompute-safe), im Prompt neben dem kuratierten Memory **klar gelabelt** gewebt.
2. **Crystallize-Reuse bestätigen:** Crystal-Output (Session-Digest) als `gist`-Basis übernehmen statt neue Zusammenfassung — Joshua bestätigt am Code.

## Aufteilung (Joshuas Regie, Tills Freigabe)

- **schmied (Capture/on-box):** saubere per-Session-Event-Streams + Event-Typ-Provenance (für `groundedness`) rausreichen; historischen Backfill durchziehen (läuft) → Korpus zum Konsolidieren; dieses Design-Doc.
- **joshua (L2/L3-Hirn):** Konsolidierung (Crystallize → automatischer Card-Writer + Tags), Card-Store, Recall (A+C). Kennt Zahnfee/Crystallize/Memory-v2/pgvector aus erster Hand.
- **Integration:** Card-Schema = Vertrag (dieses Doc) → Feature-Branches + gegenseitige PR-Reviews.

## Governance / Reihenfolge

Design-Doc (dies) → **Tills SPEC-OK als standalone-Commit** → Plan → TDD-Build → Till testet. **Nichts wird vor dem SPEC-OK gebaut.** Technische Richtung = joshuas Call; ob/wann + der SPEC-Eintrag = Tills Schnitt.

## Tests (Richtung)

- L2: Card-Generierung deterministisch testen (fixe Event-Fixtures → erwartete Tags; groundedness-Heuristik aus Event-Mix). Recompute-Idempotenz (wipe→rebuild ergibt gleiche Karten).
- L3: A lädt Top-N nach recency×salience; C trifft per Cue die richtigen Karten; Source-Trennung (auto-Karten verschmutzen kuratiertes Memory nicht).
- Token-Budget-Test: Recall-Block pro Turn unter definiertem Token-Cap.
