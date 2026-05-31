# Design: Live-Modell-SSOT — Provider-Modelle live statt hardcoded

**Datum:** 2026-05-31
**Status:** Design abgestimmt (Brainstorming mit Till). Kein Bau ohne Plan-Freigabe.
**SPEC-Bezug:** SPEC.md Zeile 252-257 fordert bereits „Modell-Catalog … Live aus dem
Provider-Endpoint … Suche + Filter". Dieses Design stellt **SPEC-Konformität her** —
es ist KEINE SPEC-Änderung. Der Code weicht ab (hardcoded `KNOWN_PROVIDERS` in der
Auswahl), nicht die SPEC.

---

## Problem (verifiziert)

Modell-Information liegt **hardgespiegelt über 6 Dateien** (Drift, „Suchproblem bei
jedem neuen Modell"):
- `frontend/.../llm/_llm_providers.ts` `KNOWN_PROVIDERS` — ~250 Modell-Strings (NVIDIA=171)
- `core/.../llm/_catalog_data.py` `STATIC_MODELS`, `METADATA`, `PROVIDER_ENDPOINTS`, `PROVIDER_PREFIX`
- `core/.../llm/_pricing.py` (Cost-Tracking)
- `frontend/.../chat/pricing.ts`

HH2 hat den Live-Fetch (`catalog.py:_fetch_live_models`, 6 Provider) **bereits gebaut**,
nutzt ihn aber nur im Admin-Katalog. Die eigentliche Modell-**Auswahl** (`ProviderForm`)
zieht aus der hardcoded `KNOWN_PROVIDERS`. Folge: nur 5 OpenRouter-Modelle wählbar, alle
bezahlt; kostenlose nicht auffindbar.

**Vorbild-Recherche:** Hermes (Tills Tool) macht es vor — `live → 5-Min-TTL-Cache →
static fallback`, zentral in einer Datei, 8s-Timeout, Fehler→Fallback. OpenClaw ist
komplett hardcoded (CLI, braucht es nicht). HH2 hat die Maschinerie, verdrahtet sie nur falsch.

## Scope-Entscheidungen (mit Till abgestimmt)

| Frage | Entscheidung |
|---|---|
| Auswahl-Ebene | **Agent wählt direkt aus Live-Liste** — keine manuelle Vorauswahl (`provider.models` entfällt als Kuratierung) |
| Cache | 5-Min-TTL im Memory, Lock gegen parallele Fetches (Hermes-Muster) |
| Pricing/free | **In v1**: `pricing` auslesen → „kostenlos"-Badge + „nur gratis"-Filter |
| Endpunktlose Provider | Anthropic wird **7. Live-Provider** (`GET /v1/models`); MiniMax + Codex bleiben statisch |
| UX bei 300+ Modellen | Such-Combobox + Provider-Gruppierung + free-Filter (SPEC: „Suche + Filter") |

## Architektur

```
Provider-API /v1/models ──┐  (live: OpenAI, NVIDIA, Groq, Mistral, OpenRouter, Gemini, Anthropic)
                          ├─► catalog.py  ──► TTL-Cache (5min, Lock) ──► GET /api/llm/catalog
STATIC_MODELS ────────────┘     + pricing/free + context              (struktur. Einträge)
  (MiniMax, Codex)                                                          │
                                                                           ▼
                                              Agent-Modell-Auswahl (_ModelTab): Such-Combobox
                                              + „kostenlos"-Badge + „nur gratis"-Toggle
```

### Backend
- **`catalog.py` erweitern:** `_fetch_live_models` liefert strukturierte Einträge statt
  nur IDs: `{id, context_window, tool_use, is_free, price_prompt, price_completion}`.
  `is_free = pricing.prompt == "0" und pricing.completion == "0"` (OpenRouter-Format).
- **Anthropic-Live:** neuer `PROVIDER_ENDPOINTS["anthropic"]` mit Auth-Modus `x-api-key`
  (Header `x-api-key` + `anthropic-version: 2023-06-01`); bei OAuth-Anthropic der
  Access-Token als `Authorization: Bearer`. Parsen wie OpenAI (`data[].id`).
- **TTL-Cache:** In-Memory dict `{provider_id: (timestamp, entries)}`, TTL 300 s,
  `asyncio.Lock` pro Provider. Bei Fetch-Fehler: letzter Cache, sonst `STATIC_MODELS`.
- **`validate_model` anpassen** (`agents/_validation.py:46`): nicht mehr gegen
  `provider.models`, sondern gegen die (gecachte) Live-Liste prüfen — **durchwinken,
  wenn keine Liste verfügbar** (Fetch-Fehler darf Agent-Speichern nie blocken). Format-
  Check bleibt. Heutiges Verhalten `if available and model not in available` degradiert
  sauber, da `available` ohne Kuratierung leer wäre.
- **Obsolet:** `_ensure_model_in_providers` + `use-in-agent`-Eintragslogik
  (`llm_catalog.py:61-99`); `provider.models` wird nicht mehr geschrieben.

### Frontend
- **`KNOWN_PROVIDERS` schrumpft** auf Provider-Metadaten (`id, name, placeholder, auth`).
  Die Modell-Arrays (~250 Strings) **entfallen**.
- **`ProviderForm` vereinfacht:** nur Provider + API-Key/OAuth. Modell-Checkboxen +
  custom-Feld entfallen.
- **`_ModelTab` (Agent-Auswahl)** wird Such-Combobox gegen `/api/llm/catalog`:
  Textsuche, Provider-Gruppierung, „kostenlos"-Badge, Toggle „nur gratis". Aktuelles
  Agent-Modell wird immer angezeigt (auch wenn Fetch leer) — bestehende Logik `_ModelTab:21`.
- **`AgentsPage`** lädt Modelle aus dem Katalog-Endpoint statt `flatMap(provider.models)`.

## Migration / kein Bruch (nach der Akte-Lektion)
- Bestehende Agenten behalten `llm_model`; Dropdown zeigt den aktuellen Wert immer.
- Bestehende `provider.models` in llm.json werden **ignoriert, nicht gelöscht** (kein
  destruktiver Eingriff). `validate_model` winkt bei leerer/fehlender Live-Liste durch.
- Provider ohne Endpoint → `STATIC_MODELS` bleibt deren Quelle.

## Drift-Elimination
Übrig bleiben nur zwei Quellen mit klarer Einzelverantwortung: `STATIC_MODELS`
(Fallback für endpunktlose Provider) und `_pricing.py` (Cost-Tracking — bewusst
separat, da Reporting feineres Pricing braucht als free/paid). `KNOWN_PROVIDERS`-
Modelllisten + `METADATA`-Pflegezwang bei neuen Modellen entfallen.

## Tests
- `catalog.py`: pricing/free-Parsing (OpenRouter-Fixture), Anthropic-Auth-Modus,
  Cache-Hit/Miss/Expiry, Fallback auf STATIC_MODELS bei Fetch-Fehler.
- `validate_model`: durchwinken bei leerer Liste, akzeptiert Live-Modell, lehnt Format-
  Unsinn ab, bricht NICHT bei Fetch-Fehler.
- Endpoint: free-Flag korrekt, strukturierte Felder.
- Frontend: `tsc -b` grün (NICHT `--noEmit` — toter Wächter, `feedback_frontend_tsc_check`).

## Nicht-Ziele (v1)
- Live-Pricing für Cost-Tracking (`_pricing.py` bleibt separat/statisch).
- MiniMax/Codex live (kein Endpoint).
- Persistenter Disk-Cache (Memory-TTL reicht; Hermes nutzt Disk, für HH2 v1 unnötig).

## Offene Implementierungs-Verifikation (im Plan)
- Anthropic `GET /v1/models` Auth genau verifizieren (x-api-key vs. OAuth-Bearer) —
  beim Bau mit echtem Key/Token testen (`feedback_verify_before_build`).
- OpenRouter `/models` pricing-Feldnamen am echten Response bestätigen.
