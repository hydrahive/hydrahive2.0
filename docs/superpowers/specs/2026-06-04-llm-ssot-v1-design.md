# LLM-SSOT v1 — Design (Sub-Projekt 1: Config-Seite + Registry-Backend)

> **Ziel:** EINE Stelle für alles LLM. Provider + Token an einem Punkt hinterlegen, alle
> Standard-Modelle an einem Punkt wählen. Eine kanonische, automatisch nach Zweck
> klassifizierte Modell-Quelle, aus der **jeder** Modell-Picker liest — gefiltert + sortiert.
> Keine Abweichungen mehr: es gibt genau einen Ort zum Anlegen/Einstellen.
>
> **Scope dieses Specs = Sub-Projekt 1:** das **Registry-Backend** (eine kanonische Quelle,
> Auto-Klassifikation, ein Endpoint, `validate_model` nutzt sie) **+ die eine LLM-Config-Seite**
> (Token + alle Standard-Modelle pro Zweck). Das Umstellen der *übrigen* Picker (Chat/Buddy/
> Agents/Projekte/Zahnfee/Media) auf die Registry + das Löschen der alten Pfade ist **Sub-Projekt 2**.
>
> **Status:** Design abgestimmt (Brainstorming 2026-06-04, Till). Anlass: Modell-Auswahl zeigt heute
> an 5+ Stellen 5+ verschiedene Listen (Diagnose unten).

---

## Entscheidungen (abgestimmt)

| Frage | Entscheidung |
|---|---|
| Modell-Quelle | **Auto-Live**: Provider+Token → alle Modelle live geholt + automatisch nach Zweck klassifiziert. Du wählst nur Defaults. Pro Provider statischer Fallback gegen Fetch-Fehler. Keine manuelle Pro-Modell-Pflege. |
| Erster Schnitt | **Config-Seite + SSOT-Backend** zuerst. Übrige Picker → Sub-Projekt 2. |
| SSOT-Architektur | **Ein Registry-Modul** `llm/registry.py` = autoritative Quelle; alte Fetcher werden interne Daten-Lieferanten dahinter; ein Endpoint; `validate_model` liest nur von hier. |
| Defaults-Speicher | `llm.json` bleibt; **ein Accessor** `get_default/set_default(zweck)` über die bestehenden Keys (kein riskantes Key-Umbenennen in SP1). |
| Endpoint-Rechte | Modelle lesen = `require_auth` (Picker für alle, fixt 403). Token/Defaults setzen = `require_admin`. |

---

## Ist-Zustand (Diagnose — warum überall andere Modelle)

Heute existieren ≥5 getrennte Modell-Quellen (verifiziert, `code-explorer`-Map 2026-06-04):

1. **LLM-Settings → Standard-Modell** liest nur die manuell gepinnten `provider.models` aus `llm.json` (`LlmPage.tsx:23`) → erklärt „nur 4 NVIDIA", Live-Katalog ignoriert.
2. **Chat/Agent/Projekt-Picker** = `llmInfoApi.getModels()` (`agents/api.ts:39`) merged `/api/llm` + `/api/llm/catalog` (Live ∪ custom).
3. **Buddy-Switcher** = `/api/buddy/models` → `commands.list_models` → `_available_models()` (`agents/_validation.py:45`) = In-Memory-`_cache` ∪ `provider.models` (kalt nach Neustart, kein Anthropic-Fallback).
4. **`validate_model`** (`_validation.py:68`) = dieselbe `_available_models()` → lehnt claude ab, wenn Anthropic-Live-Fetch 401t (nicht im Cache, nicht gepinnt) → „rastet nicht ein", obwohl der Picker es zeigt.
5. **Embed / TTS / STT / Video** = drei weitere getrennte Quellen: `embed.py:EMBED_MODELS` (Hardcode-Tabelle), `media_models.py` (eigene OpenRouter-Modalitäts-Endpoints + eigene Caches `_speech/_transcribe/_video`).

Dazu: `/api/llm` + `/api/llm/catalog` sind **admin-only** → normale User bekommen 403 → leerer Picker.

---

## Architektur

```
Provider + Token  (llm.json: providers[])
        │
        ▼
  core/src/hydrahive/llm/registry.py   ◄── DIE autoritative Quelle
   • holt live von jedem konfigurierten Provider (orchestriert die heutigen Fetcher intern)
   • klassifiziert jedes Modell in eine Zweck-Menge {chat,embed,tts,stt,image,video,music}
   • EIN gemeinsamer Cache (TTL, beim Start vorgewärmt) + pro-Provider statischer Fallback
        │
        ├──► GET /api/llm/models[?modality=<zweck>]   (require_auth)
        │         └─ gefilterte + sortierte kanonische Liste
        ├──► validate_model() / validate_compact_model() / validate_fallback_models()  lesen NUR von hier
        ├──► get_default(zweck) / set_default(zweck, modell)   (Defaults-Accessor über llm.json)
        └──► LLM-Config-Seite (Token + alle Standard-Modelle)
              (Sub-Projekt 2: ALLE übrigen Picker lesen NUR von hier)
```

Eine Quelle, eine Klassifikation, ein Cache, ein Endpoint, ein Validierungs-Pfad, ein Defaults-Pfad.

---

## Komponenten

### 1. `core/src/hydrahive/llm/registry.py` — die kanonische Quelle (NEU)

Eine `ModelEntry` (dataclass, frozen):
```
id: str                      # vollständige Routing-ID (wie heute, z.B. "openrouter/...", "claude-...")
provider: str                # provider-id
label: str                   # Anzeigename (sortierbar)
purposes: frozenset[str]     # Teilmenge von {chat,embed,tts,stt,image,video,music}; ein Modell kann mehrere
context_window: int | None
is_free: bool | None
embed_dim: int | None        # nur bei embed
source: "live" | "fallback"  # woher (für Debug/Anzeige)
```

Öffentliche Funktionen:
- `list_models(modality: str | None = None) -> list[ModelEntry]` — alle Einträge (gemerged Live ∪ Fallback, dedupliziert per id), bei `modality` gefiltert auf `modality in entry.purposes`, **sortiert** (provider, dann label). Das ist die einzige Liste-Quelle.
- `is_known(model_id: str) -> bool` — für `validate_model` (True wenn id in der kanonischen Liste; bei komplett leerer Liste → True, Failopen wie heute).
- `warm() -> None` / `async awarm()` — füllt den Cache (beim Lifespan-Start gerufen, fixt cold-cache).
- `invalidate() -> None` — Cache leeren (nach `PUT /api/llm` Token-Änderung).

Interne Daten-Lieferanten (bestehender Code wird dahinter genutzt, NICHT dupliziert):
- **chat/vision/code/reasoning/…** → `catalog.catalog_for_providers(providers)` (Live-`/models` je Provider) → Klassifikation via `METADATA.category` + Modalitäten.
- **embed** → `embed.EMBED_MODELS` (mit Dimension) wandert als Zweck `embed` in die Registry (eine Quelle für Embed, statt separat).
- **tts** → `media_models.list_speech_models()`; **stt** → `list_transcribe_models()`; **video** → `list_video_models()` (die spezialisierten OpenRouter-Endpoints, intern gerufen + als Zweck getaggt).
- **image / music** → aus dem Chat-Katalog via `output_modalities` (image bzw. audio-nicht-speech).

> Wichtig: die Registry ist die einzige Stelle, die diese Lieferanten zusammenführt + klassifiziert + cached. Niemand sonst ruft sie direkt für Listen (in SP2 werden die alten Direkt-Aufrufe entfernt).

### 2. Klassifikation (automatisch, deterministisch)
- Reihenfolge der Zweck-Zuordnung pro Modell:
  - in `EMBED_MODELS` → `embed` (+ `embed_dim`).
  - von `list_speech_models` → `tts`; `list_transcribe_models` → `stt`; `list_video_models` → `video`.
  - `output_modalities` enthält `image` → `image`; enthält `audio` (und nicht reine speech) → `music`.
  - sonst (LLM/`METADATA.category` ∈ {chat,code,reasoning,vision,safety,specialized,translation} **oder unbekannt**) → `chat`.
- Ein Modell mit mehreren Treffern bekommt mehrere Zwecke (multimodal erscheint in mehreren Pickern).
- Unbekanntes Modell → mindestens `chat` (nie unsichtbar).

### 3. Cache + Fallback
- Ein Cache in `registry.py` (Wiederverwendung des 300s-TTL-Musters aus `catalog.py`). **Beim Lifespan-Start vorgewärmt** (`registry.awarm()` nach `init_db`/Provider-Load) → Picker nie kalt nach Neustart.
- Pro Provider eine statische Fallback-Liste (bestehende `STATIC_MODELS` + aktuelle Anthropic-Modelle inkl. der 7 claude). Live-Fetch leer/Fehler (z.B. 401) → Fallback wird genutzt **und** zählt für `validate_model`. → claude bleibt wählbar trotz kaputtem Key.
- `invalidate()` nach Token-Änderung (`PUT /api/llm`), damit neue Keys sofort greifen.

### 4. Endpoint `GET /api/llm/models` (NEU)
- Query `?modality=chat|embed|tts|stt|image|video|music` (weglassen → alle).
- `dependencies=[Depends(require_auth)]` (jeder Picker, auch non-admin → fixt 403).
- Antwort: `{ "models": [ {id,label,provider,purposes,context_window,is_free,embed_dim} … ] }` (sortiert).
- Liegt in `api/routes/llm.py` (oder dünnes `llm_models.py`), liest `registry.list_models(modality)`.

### 5. `validate_model` zieht auf die Registry um
- `agents/_validation.py`: `_available_models()` + `validate_model()` + `validate_compact_model()` + `validate_fallback_models()` lesen `registry.is_known(...)` / `registry.list_models()` statt direkt `catalog._cache` ∪ `provider.models`.
- Wirkung: **sofort global** — Buddy/Chat/Agent-Set-Pfade validieren gegen dieselbe Liste, die der Picker zeigt. claude-Bug überall weg, schon in SP1 (vor der Picker-Migration in SP2).

### 6. Defaults-Accessor (ein Code-Pfad)
- Neu z.B. in `llm/_config.py`: `get_default(purpose) -> str` / `set_default(purpose, model) -> None`.
- Zweck→Storage-Key-Mapping (bestehende Keys in `llm.json`, **nicht umbenannt** in SP1):
  `chat→default_model`, `embed→embed_model`, `image→media_models.image`, `music→media_models.music`, `tts→media_models.tts`, `stt→media_models.transcribe`, `video→media_models.video`.
- Alle bisherigen Direkt-Leser (`client.default_model()`, embed-Leser, `media_models.get_media_model()`, datamining) rufen künftig den Accessor → ein Pfad. (Verhalten identisch, nur zentralisiert.)

### 7. Die EINE LLM-Config-Seite (Frontend)
Säubert die heutige `features/llm/LlmPage.tsx`, zwei klare Bereiche:
1. **Provider & Token** — Provider anlegen/bearbeiten, API-Key oder OAuth verbinden, Verbindung testen. (Bestehende `ProviderCard`/`ProviderForm` weiternutzen, gesäubert.)
2. **Standard-Modelle** — je ein Selektor für **Chat · Embedding · Bild · Musik · TTS · STT · Video**, jeder gespeist aus `GET /api/llm/models?modality=<zweck>` (gefiltert + sortiert). Speichern → `set_default(zweck, …)` via `PUT /api/llm` bzw. ein dünner Defaults-Endpoint.
- Das ist der eine Punkt für Token + alle Standard-Modelle.

---

## Datenfluss

- **Seite laden:** Config-Seite holt `GET /api/llm` (Provider/Defaults) + je Zweck `GET /api/llm/models?modality=` (gefilterte Liste). Selektoren zeigen aktuellen Default markiert.
- **Default setzen:** Auswahl → `set_default(zweck, model)` persistiert in `llm.json`.
- **Token ändern:** `PUT /api/llm` → `registry.invalidate()` → nächster Fetch nutzt neuen Key.
- **Picker lesen (heute SP1: nur Config-Seite; SP2: alle):** `GET /api/llm/models?modality=` → kanonische Liste.
- **Modell setzen (Agent/Buddy):** Set-Pfad ruft `validate_model` → `registry.is_known` → akzeptiert genau, was der Picker zeigt.

## Fehlerbehandlung
- Provider-Live-Fetch schlägt fehl (401/Timeout/leer) → statischer Fallback dieses Providers; geloggt (WARNING), nicht still geschluckt; Liste bleibt nutzbar.
- Komplett leere Registry (Erst-Setup, kein Provider) → `validate_model` winkt durch (Failopen, wie heute), Picker zeigt leer.
- Token/Default-Schreiben nur `require_admin`; Lesen `require_auth`.

## Tests
- **Backend (pytest):** Klassifikation (Modell → korrekte Zweck-Menge, multimodal → mehrere); `list_models(modality)` filtert + sortiert; Fallback greift bei Fetch-Fehler und ist in der Liste; `validate_model` akzeptiert ein Fallback-claude trotz simuliertem 401, lehnt Unbekanntes ab, winkt bei leerer Registry durch; Defaults-Accessor liest/schreibt die richtigen Keys; Endpoint `?modality=` filtert + ist für non-admin erreichbar (require_auth).
- **Frontend:** Config-Seite baut (`npm run build`), jeder der 7 Selektoren füllt sich aus seiner Modalität, eslint grün.
- **Live-E2E auf `.23` (Till):** Token setzen → Verbindung testen; pro Zweck Default wählen → persistiert nach Reload; ein Agent/Buddy lässt sich auf claude wechseln (validate gegen Registry); kalt nach Neustart trotzdem voll (warm-at-start).

## Bewusst NICHT in SP1 (YAGNI / → Sub-Projekt 2)
- Umstellen der übrigen Picker (`ModelPicker`, Buddy-Switcher, Agent-`_ModelTab`/`NewAgentDialog`/`CompactionSection`/Fallback, `NewProjectDialog`, Zahnfee, `BuddySettingsCompaction`, `MediaModelsSection`) auf `GET /api/llm/models` + Löschen der alten Pfade (Frontend-`getModels`-Merge, `_available_models`-Cache-Read, separate Media-Caches, `provider.models`-Pflege-UI).
- Manuelles Pro-Modell Ein/Ausblenden oder Custom-Modelle (war „Hybrid" — abgelehnt).
- Umbenennen der `llm.json`-Default-Keys auf eine `defaults`-Map (Accessor reicht; reine Kosmetik, später optional).
- Konsolidieren der alten Endpoints (`/embed-models`, `/speech-models`, …) — bleiben in SP1 koexistent (von Alt-Pickern genutzt), fallen in SP2.

## Zerlegung (Kontext — eigene Specs je Sub-Projekt)
1. **Dieses Spec:** Registry-Backend + Config-Seite + validate-Umzug + Defaults-Accessor.
2. Alle übrigen Picker auf die Registry umstellen + alte Pfade/Quellen entfernen (die „keine Abweichungen"-Durchsetzung).
3. (optional) Speicher-Normalisierung (`defaults`-Map), Alt-Endpoints abräumen.

## In der Planungs-Phase zu klären (Detail, kein Design-Blocker)
- Genaue `ModelEntry`-Felder + ob das Frontend mehr Metadaten braucht (free-Badge, Kontextfenster) in den Selektoren.
- Ob der Defaults-Schreibpfad über das bestehende `PUT /api/llm` läuft oder ein dünner `PUT /api/llm/defaults`.
- Startup-Warm: synchron im Lifespan vs. Hintergrund-Task (Start nicht blockieren).
- image-vs-music-Abgrenzung über `output_modalities` (audio→music nur wenn nicht speech).
