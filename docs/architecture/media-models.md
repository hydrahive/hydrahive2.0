# Media-Modelle — zentrale Verwaltung

**Last Updated:** 2026-06-01

Seit 2026-06 werden KI-Modelle für Media-Kategorien zentral in einer Datei verwaltet,
nicht über 5+ Stellen verteilt. Das verhindert Drift zwischen Frontend und Backend.

## Problem & Lösung (SSOT)

**Vorher:** Modell-Listen wurden hardcoded in:
- Frontend `llm/MediaModelsSection.tsx`
- Backend `catalog.py`
- Installer `modules/50-systemd.sh`
- Verschiedene Tool-Defaults

→ Lead zu Drift (fehlende Modelle, alte Namen, Inconsistenz).

**Nachher:** Eine Quelle (`llm/media_models.py`), drei APIs:
- Live-Fetch mit TTL-Cache
- Fallback-Listen wenn API offline
- Per-Agent-Konfiguration in `media_models` Dict

## Zentrale Datei

**`core/src/hydrahive/llm/media_models.py`**

```python
DEFAULTS: dict[str, str] = {
    "image": "openai/gpt-5-image-mini",
    "music": "google/lyria-3-pro-preview",
    "tts": "hexgrad/kokoro-82m",
    "transcribe": "openai/whisper-large-v3",
    "video": "kling/kling-video-v2-master",
}

# Kategorien die aus dem Chat-Katalog kommen (Bild, Musik)
_CATEGORY_MODALITY: dict[str, tuple[str, str]] = {
    "image": ("output", "image"),
    "music": ("output", "audio"),
    "transcribe": ("input", "audio"),
}

# APIs für Speech + Transcribe + Video
async def list_speech_models(force=False) -> list[dict]
async def list_transcribe_models(force=False) -> list[dict]
async def list_video_models(force=False) -> list[dict]
```

### TTL-Cache

Jede API lädt live, speichert aber:
- **TTL:** 300s (5 Min) für die gecachte Liste
- **Fallback:** hardcoded Liste wenn OpenRouter offline
- **Force:** `?force=true` erzwingt frischen Fetch

```python
_SPEECH_MODELS_URL = "https://openrouter.ai/api/v1/models?output_modalities=speech"
_SPEECH_TTL = 300.0
_speech_cache: tuple[float, list[dict]] | None = None
```

## Kategorien (Schnittstellen zu den Tools)

### Bild (`image`)
- Tool: `generate_image.py`
- Quelle: Chat-Katalog (Provider-Filter auf output-Modalität `image`)
- Modelle: DALL-E, Flux, DeepSeek, LumaAI
- Default: `openai/gpt-5-image-mini` (schnell, günstig)
- Frontend: Catalog-basiert, Dropdown-Auswahl

### Musik (`music`)
- Tool: `generate_music.py` (optional, noch nicht aktiv in Cluster)
- Quelle: Chat-Katalog (output-Modalität `audio`)
- Modelle: Google Lyria, HunYuan Music
- Default: `google/lyria-3-pro-preview`
- Frontend: Catalog-basiert, Dropdown

### TTS — Sprache (`tts`)
- Tool: Voice-Subsystem `/audio/speech` → Browser + incus-Container
- Quelle: Live von `/models?output_modalities=speech`
- Modelle: Kokoro (schnell, lokal), E2-Voice (teuer, natürlich)
- Default: `hexgrad/kokoro-82m`
- Frontend: `MediaModelsSection` Dropdown mit Live-Liste
- **Wichtig:** ist ein echtes Speech-Modell (Audio-Output), NICHT gpt-audio (Text-Konversation)

### Transkription (`transcribe`)
- Tool: `transcribe_audio.py`
- Quelle: Live von `/models?input_modalities=audio`
- Modelle: Whisper (OpenAI, bestes offenes), andere STT-APIs
- Default: `openai/whisper-large-v3`
- Frontend: `MediaModelsSection` Dropdown mit Live-Liste
- Sprache: Optional im Tool-Parameter, Auto-Detect default

### Video (`video`)
- Tool: `generate_video.py`
- Quelle: Live von `/videos/models`
- Modelle: Kling v2 (default), Veo 3.1, Sora 2 Pro, Hailuo 2.3
- Default: `kling/kling-video-v2-master`
- Frontend: `MediaModelsSection` Dropdown mit Live-Liste
- Poll-Timeout: 300s, exponentiell backoff

## Embedding (`embed_model`)

Das Embedding-Modell steht NICHT in `media_models` sondern separat in `llm.json`:

```json
{
  "embed_model": "voyage/voyage-3-large",
  "media_models": {
    "image": "openai/gpt-5-image-mini",
    "tts": "hexgrad/kokoro-82m",
    ...
  }
}
```

**Grund:** Embedding braucht immer die echte Dimension (`embed_dim`) — diese Modelle haben
eine feste API-Schnittstelle (Query→Vector), nicht call-specific wie Video.

## Konfiguration

### User-Ebene (Agent-Config)

Jeder Agent hat seine Media-Modell-Overrides in `llm.json`:

```json
{
  "agents": {
    "architect": {
      "model": "claude-3-5-sonnet-20241022",
      "media_models": {
        "image": "openai/gpt-5-image-large",  // Override default
        "video": "openai/sora-2-pro"
      }
    }
  }
}
```

**Lesen im Tool:**
```python
from hydrahive.llm.media_models import get_media_model

model = get_media_model("video", config)  # Gibt Agenten-Override oder Default
```

**Tool-Parameter überschreibt Agent-Config:**
```json
{
  "tool_call": {
    "generate_video": {
      "model": "google/veo-3.1"  // Dieser Parameter gewinnt
    }
  }
}
```

### Frontend-Picker

`features/llm/MediaModelsSection.tsx`:

```tsx
// Katalog-Modelle (Bild, Musik) — aus Chat-Katalog
CatalogModels = catalog.providers
  .flatMap(p => p.models)
  .filter(m => m.output === "image")

// Live-Modelle (TTS, Transcribe, Video)
SpeechModels = await llmApi.getSpeechModels()
TranscribeModels = await llmApi.getTranscribeModels()
VideoModels = await llmApi.getVideoModels()
```

## API-Endpoints

**`GET /api/llm/speech-models`** (Admin-only)
```json
[
  { "id": "hexgrad/kokoro-82m", "name": "Kokoro (fast)", "features": [...] },
  { "id": "openai/tts-1-hd", "name": "OpenAI TTS HD", "features": [...] },
  ...
]
```

**`GET /api/llm/transcribe-models`** (Admin-only)
```json
[
  { "id": "openai/whisper-large-v3", "name": "Whisper v3", "languages": 99, ... },
  ...
]
```

**`GET /api/llm/video-models`** (Admin-only)
```json
[
  { "id": "kling/kling-video-v2-master", "name": "Kling v2", "duration_max": 1080, ... },
  { "id": "google/veo-3.1", "name": "Veo 3.1", "duration_max": 2400, ... },
  ...
]
```

## Fallback-Listen

Falls OpenRouter offline ist oder ein HTTP-Fehler passiert, nutzt das System
hardcoded Listen als Fallback:

```python
_FALLBACK_SPEECH_MODELS = [
    {"id": "hexgrad/kokoro-82m", "name": "Kokoro 82M"},
    {"id": "openai/tts-1-hd", "name": "OpenAI TTS HD"},
]

_FALLBACK_VIDEO_MODELS = [
    {"id": "kling/kling-video-v2-master", "name": "Kling Video v2"},
    {"id": "google/veo-3.1", "name": "Google Veo 3.1"},
]
```

→ Die Tools arbeiten noch, aber mit reduzierter Auswahl.

## Model-Validierung

**`validate_model(model: str, config: dict) -> bool`**

Prüft ob ein Modell für eine Kategorie erlaubt ist:

- Prüft gegen Live-Liste (wenn verfügbar)
- Fallback: akzeptiert alles (wenn Live-Liste leer/offline)
- Tool-Parameter `model` bypassed die Validierung (Agent sagt "ich nehme dieses Modell")

## Fehlerbehandlung

| Szenario | Verhalten |
|---|---|
| OpenRouter offline, erste Anfrage | Fallback-Liste zurückgeben |
| TTL abgelaufen, neue Anfrage | Live-Fetch versuchen, bei Fehler Fallback |
| Tool-Parameter `model` ungültig | Tool antwortet mit "unknown model", Agent adaptet |
| Keine Credentials für OpenRouter | speech/transcribe/video-Endpoints liefern Fallback |

## Beste Praktiken

1. **Cache respektieren** — nicht jeden Call neu fetchen
2. **Fallback-Listen aktuell halten** — wenn neue Modelle Standard werden, in Fallback-Listen aufnehmen
3. **Credentials guarden** — `openrouter_key()` prüft API-Key vor Use
4. **Frontend: null-safe** — wenn API offline, zeige Fallback-Modelle ohne Fehler
5. **Tests:** seeded mit Test-Modellen, nicht echte API-Calls

## Zusammenfassung

| Kategorie | Tool | Quelle | Live-API | Fallback | Default |
|---|---|---|---|---|---|
| `image` | `generate_image` | Chat-Katalog | nein | — | gpt-5-image-mini |
| `music` | `generate_music` | Chat-Katalog | nein | — | lyria-3-pro |
| `tts` | Voice-Subsystem | `/models?output=speech` | **ja** | 5 Modelle | kokoro-82m |
| `transcribe` | `transcribe_audio` | `/models?input=audio` | **ja** | 3 Modelle | whisper-large-v3 |
| `video` | `generate_video` | `/videos/models` | **ja** | 4 Modelle | kling-video-v2 |
| `embed_model` | `datamining_search` | separat | nein | — | bge-m3 |

**Dateien:**
- Backend: `core/src/hydrahive/llm/media_models.py`, `core/src/hydrahive/api/routes/llm.py`
- Frontend: `frontend/src/features/llm/MediaModelsSection.tsx`, `frontend/src/features/llm/api.ts`
