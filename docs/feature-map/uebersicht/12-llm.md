# Feature Map: LLM — Provider-Catalog, Registry & Modell-Verwaltung

> **Modul:** `core/src/hydrahive/llm/`  
> **Was:** Zentrale Verwaltung aller LLM-Provider und Modelle. **Eine kanonische Registry** aggregiert Chat-Katalog, Media- und Embed-Modelle. Alle Picker lesen denselben Endpoint.  
> **Warum:** Ohne korrekte Modell-Configs: Routing-Fehler, falsche Preise, tote Failover-Listen. Vor dem SSOT-Umbau: 6+ divergierende Listen; Modell-Switch-Bug (claude selektierbar auch bei 401).

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `registry.py` | **Kanonische SSOT.** Aggregiert catalog/media/embed intern. `list_models(modality?)` (async, gecacht), `known_ids()`/`is_known()` (sync, für validate). Cache-TTL 300s, leere Liste wird nicht gecacht. |
| `catalog.py` | Live-Fetch von `/v1/models` je Provider. 5-Min-TTL-Cache. Fallback auf `STATIC_MODELS`. |
| `_config.py` | `load_config()` (mtime-Cache), `get_default(purpose)`/`set_default(purpose, model)` — Defaults-Accessor über `llm.json`. `_PURPOSE_KEYS` mappt Zweck → Pfad in `llm.json`. |
| `_pricing.py` | Preis-Lookup: `cost_micros(model, input_tokens, output_tokens)`. `provider_from_model()`. |
| `media_models.py` | Live-Listen für TTS/Transcribe/Video (OpenRouter). Fallback-Listen. Weiterhin von der Registry intern genutzt. |
| `embed.py` | Embed-Modelle + `aembed_batch`. Weiterhin von der Registry intern genutzt. |

---

## registry.py — die neue kanonische SSOT

```python
# Async: gebaut + gecacht, optional nach Zweck gefiltert
await list_models(modality="chat")   → [ModelEntry, ...]
await list_models(modality="tts")    → [ModelEntry, ...]
await list_models()                  → alle Zwecke

# Sync (kein Fetch — für validate):
known_ids()  → set[str]      # leere Menge wenn Cache kalt
is_known(model_id)  → bool   # True bei leerem Cache (fail-open)

# Startup-Vorwärmung (in lifespan.py):
await awarm()                        # blockiert Startup nicht

# Cache leeren (z.B. nach config-PUT):
invalidate()
```

**Zwecke (`PURPOSES`):** `chat`, `embed`, `tts`, `stt`, `image`, `video`, `music`

**`ModelEntry` (frozen dataclass):** `id`, `provider`, `label`, `purposes: frozenset[str]`,
`context_window`, `is_free`, `embed_dim`, `source` (`"live"` | `"fallback"`)

**Build-Logik:** Chat-Katalog → je Eintrag `_classify_catalog_entry` (chat + image/music aus
output_modalities); Embed-Modelle; TTS/STT/Video via `list_speech_models`/`list_transcribe_models`/
`list_video_models`. Dedupliziert per id, Zweck-Mengen werden vereinigt.
Leere Builds werden **nicht** gecacht → nächster Aufruf retryt automatisch.

---

## _config.py — Defaults-Accessor

```python
get_default("chat")   → "claude-sonnet-4-6"   # aus llm.json default_model
get_default("tts")    → "hexgrad/kokoro-82m"   # aus llm.json media_models.tts
get_default("stt")    → ...                    # aus llm.json media_models.transcribe
set_default("image", "openai/gpt-5-image-mini")  # schreibt llm.json, invalidiert Cache
```

`_PURPOSE_KEYS` mappt jeden Zweck auf seinen Pfad in `llm.json`
(z.B. `"stt"` → `("media_models", "transcribe")`). SSOT für alle Defaults.

---

## _pricing.py

```python
cost_micros(
    model="claude-opus-4-5",
    input_tokens=1000,
    output_tokens=500,
    cache_creation_tokens=0,
    cache_read_tokens=0,
) → int  # Kosten in Mikro-USD (1_000_000 = $1.00)

provider_from_model("gpt-4o") → "openai"
provider_from_model("claude-3-5-sonnet") → "anthropic"
provider_from_model("openrouter/...") → "openrouter"
```

---

## LLM-API-Endpoints (aus routes/llm.py)

| Endpoint | Auth | Beschreibung |
|---|---|---|
| `GET /api/llm/models?modality=` | require_auth | **Kanonische Liste** aus Registry, gefiltert nach Zweck. Liefert `{models, default}`. ALLE Picker nutzen diesen einen Endpoint. |
| `GET /api/llm/catalog` | admin | Kompletter Provider-Katalog (CatalogPage, Admin). |
| `GET /api/llm/effort-models` | require_auth | SSOT für xhigh/max-fähige Modell-Prefixe. |
| `GET /api/llm` | admin | Ganze `llm.json` (Config-Page). |
| `PUT /api/llm` | admin | Config speichern, triggert `registry.invalidate()`. |

**Gelöschte Routen (SP1):** `/api/llm/embed-models`, `/api/llm/speech-models`,
`/api/llm/transcribe-models`, `/api/llm/video-models` — alle ersetzt durch `/api/llm/models?modality=`.
Die Fetcher-Funktionen in `media_models.py`/`embed.py` existieren weiter, werden aber nur noch
intern von der Registry genutzt, nicht mehr direkt als Endpoints.

---

## Frontend-Nutzung

Alle Picker lesen `llmModelsApi.byModality(modality)` → `GET /api/llm/models?modality=`.

| Komponente | Zweck |
|---|---|
| `features/llm/DefaultModelsSection.tsx` | **Eine** Config-Sektion für alle 7 Zwecke (chat/embed/image/music/tts/stt/video). Löst `MediaModelsSection.tsx` ab. |
| `features/llm/api.ts` — `llmModelsApi.byModality` | Typisierter Client für `/llm/models`. |
| `features/chat/ModelPicker.tsx` | Chat-Modell-Auswahl (byModality("chat")). |
| `features/chat/commands.ts` | /model-Command (byModality("chat")). |
| `features/agents/AgentsPage.tsx` | Agent-Modell-Tab (byModality("chat")). |
| `features/buddy/BuddySettingsPage.tsx` | Buddy-Modell-Picker (byModality("chat")). |
| `features/projects/NewProjectDialog.tsx` | Projekt-Modell-Auswahl (byModality("chat")). |

**`MediaModelsSection.tsx` gelöscht** (war: separate Selects pro Kategorie gegen die alten
Modality-Endpoints). Ersetzt durch `DefaultModelsSection.tsx`.

**Hinweis:** Manuell getippte Custom-Modelle (in `provider.models` in `llm.json` eingetragen)
erscheinen NICHT im Dropdown, solange sie nicht durch den Live-Fetch zurückkommen — bewusste
Entscheidung (Registry-Konsistenz).

---

## validate_model → Registry

`agents/_validation.py::_available_models()` liest jetzt `registry.known_ids()` statt direkt
aus `catalog._cache`. Fix für den Modell-Switch-Bug: `validate_model` blockte zuvor Modelle
die im statischen Fallback-Katalog (bei 401-Providern) nicht auftauchten.
Fail-open-Semantik bleibt: leere Menge (Cache kalt) = durchwinken.

---

## OpenRouter-Gratis-Modelle

`:free`-Modelle (z.B. `deepseek-v4-flash:free`) können trotz Verfügbarkeit im Katalog
mit 429/404 antworten — das ist OpenRouters Data-Policy (Logging-Zustimmung unter
https://openrouter.ai/settings/privacy nötig für free tier). Kein HH2-Bug.

---

## Verwandte Subsysteme

- **→ Runner** (`01-runner.md`): nutzt `validate_model()` (über Registry), `_pricing.cost_micros()`
- **→ Compaction** (`06-compaction.md`): `tokens.context_window_for(model)`
- **→ Multimodal** (`27-multimodal.md`): `media_models.py` intern in Registry; Tools nutzen `get_media_model`
- **→ OAuth** (LLM-Seite): OAuth-Flows für Anthropic/OpenAI in `oauth/`
