# Memory v2 Pipeline

> Wie HydraHive2 langfristiges Wissen aus Sessions extrahiert und beim
> nächsten Session-Start in den System-Prompt einwebt.

## Pipeline-Stufen

```
Tool-Call
    │
    ▼  record_observation (in tools/_observations.py)
RawObservation                                     ── jsonl, append-only
{id, agent_id, session_id, tool_name, args, result, files?, compressed: false}
    │
    ▼  compress_session (LLM, in tools/_compress.py)
CompressedObservation                              ── jsonl, append-only
{id, raw_observation_id, agent_id, session_id, summary, files?}
    │  (am Session-Ende, Batch von 30)
    ▼  crystallize_session (LLM, in tools/_crystallize.py)
Crystal                                             ── jsonl, append-only
{id, session_id, project, narrative, key_outcomes, files_affected, lessons}
+
Lessons                                             ── memory.json (Memory v2 Store)
{lesson.<fp>: {content, confidence: 0.6, project, ...}}
    │
    ▼  build_memory_context (deterministisch, in agents/_context_injection.py)
System-Prompt-Block                                ── injiziert beim nächsten
"## Memory — What I've learned in past sessions    Session-Start desselben Agents
 ### Recent Sessions
 - <crystal narrative>
 ### Lessons Learned
 - <lesson content>"
```

## Storage-Files (pro Agent)

```
{agents_dir}/<agent_id>/
├── observations.jsonl        — RawObservations (compressed: bool)
├── compressed.jsonl          — CompressedObservations
├── crystals.jsonl            — Crystals (append-only versioniert; Re-Crystallize
│                                schreibt neuen Eintrag, get_crystal liefert neuesten)
└── memory.json               — Memory v2 Store (lessons + andere Memory-Keys)
```

## Trigger-Logik

| Stufe | Wann ausgelöst |
|---|---|
| `record_observation` | nach jedem Tool-Call (Erfolg + Failure) im Runner-Loop |
| `compress_session` | am Session-Ende (`session_end`-Hook), oder manuell |
| `crystallize_session` | von `compress_session` automatisch, wenn ≥ `MIN_OBSERVATIONS` (=5) |
| `build_memory_context` | beim Session-Start im Runner — vor jedem LLM-Call der ersten Iteration |

## Per-Agent-Konfiguration

Defaults in `agents/_defaults.py`, Overrides als Feld am Agent-Config:

| Feld | Default | Effekt |
|---|---|---|
| `memory_max_crystals` | 5 | wie viele letzte Session-Digests injizieren. 0 = aus |
| `memory_max_lessons` | 10 | wie viele Lessons (sortiert nach Confidence) |
| `memory_min_lesson_confidence` | 0.6 | Schwelle unter der Lessons ignoriert werden |
| `memory_max_chars` | 4000 | Soft-Cap für gesamten Memory-Block |
| `memory_crystal_scope` | `project_and_global` | siehe unten |

### Crystal-Scope (#113)

| Wert | Verhalten |
|---|---|
| `project_and_global` | Project-Agent sieht eigene Crystals + globale (project=None, z.B. Master-Buddy). Default. |
| `project_only` | strikt nur eigene Project-Crystals. Privacy-Use-Case. |

Implementiert via `list_crystals(include_global=...)` in `tools/_crystallize_storage.py`.

## Append-Only Versioning (#114)

`crystals.jsonl` ist append-only. Bei Re-Crystallize (`force=True`) wird ein
neuer Crystal angefügt — alter bleibt erhalten. `get_crystal()` liest das
File komplett und liefert den neuesten Match per `session_id`. `list_crystals()`
dedupliziert per `session_id` (last-write-wins).

Konsequenz: Crystal-Datei wächst über die Lebenszeit des Agents. Ein
Cleanup-Job ist denkbar (drop old versions), aktuell nicht implementiert.

## Bulk-Writes (#116, #B1)

Memory v2 Store (`memory.json`) wird komplett gelesen + geschrieben pro
Update — N Updates = N Read+Write. Daher:

- `mark_compressed_bulk(agent_id, session_id, mappings)` — ein Read+Write
  für die ganze Compress-Batch (war: N pro Observation)
- `write_keys_bulk(agent_id, entries)` — ein Read+Write für N Memory-Keys.
  Genutzt in `_save_lessons` (Crystallize-Output).

Pure Mutation isoliert in `_apply_write()` damit beide Pfade (Single + Bulk)
identische Logik haben.

## Token-Reduktion (Empty-Search-Budget)

Datamining-Tools (`datamining_search` / `datamining_timeline` / `datamining_today`)
sind opt-in per `longterm_memory: true` am Agent. Der eingewobene
System-Prompt-Block (`_runner_setup.py:_LONGTERM_MEMORY_PROMPT`) instruiert
explizit: nach 2× `count: 0` aufhören. Das verhinderte ~50% Token-Verbrauch
beim Buddy-Agent (verifiziert auf hh2-218, 2026-05-09).

## Wichtige Dateien

| Datei | Verantwortung |
|---|---|
| `tools/_observations.py` | RawObservation-Storage, `mark_compressed_bulk` |
| `tools/_compress.py` | LLM-Pipeline RawObs → CompressedObs |
| `tools/_compress_storage.py` | CompressedObservation-jsonl |
| `tools/_crystallize.py` | LLM-Pipeline CompressedObs → Crystal + Lessons |
| `tools/_crystallize_storage.py` | Crystal-jsonl, append-only versioniert |
| `tools/_memory_store.py` | Memory v2 Public-Facade |
| `tools/_memory_io.py` | `_apply_write`, `write_key`, `write_keys_bulk` |
| `tools/_memory_model.py` | Pure Functions (Confidence, Contradictions, Project-Match) |
| `agents/_context_injection.py` | `build_memory_context` |
| `runner/_runner_setup.py` | Longterm-Memory-Tool-Injection |

## Tests

- `test_memory_store.py` (32) — Pure Functions
- `test_observations.py` (8) — RawObs + Bulk-Mark
- `test_memory_bulk.py` (9) — `write_keys_bulk`
- `test_crystallize_storage.py` (11) — Append-only Versioning
- `test_memory_context_injection.py` (12) — Per-Agent-Override + Crystal-Scope
