# Feature Map: LLM — Provider-Catalog & Modell-Verwaltung

> **Modul:** `core/src/hydrahive/llm/`  
> **Was:** Zentrale Verwaltung aller LLM-Provider und Modelle. Live-Fetch von Modell-Listen.  
> **Warum:** Ohne korrekte Modell-Configs: Routing-Fehler, falsche Preise, tote Failover-Listen.

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `catalog.py` | **SSOT für alle Modelle.** Live-Fetch von `/v1/models` je Provider. 5-Min-TTL-Cache. |
| `_pricing.py` | Preis-Lookup: `cost_micros(model, input_tokens, output_tokens)`. `provider_from_model()`. |
| `media_models.py` | **SSOT für Media-Modelle** (TTS, Video, Transcribe, Bild, Musik). Live-Fetch. Fallback-Listen. |
| `_model_meta.py` | Modell-Metadaten (Context-Window, Features, ...) |

---

## catalog.py — das Herz

```python
# Live-Fetch von Modell-Listen:
list_models(provider="openrouter") → [ModelInfo, ...]
list_models(provider="anthropic") → [ModelInfo, ...]
# ...für alle 7 konfigurierten Provider

validate_model(model_id: str) → bool
# Prüft ob Modell existiert (gegen Live-Liste)
# Bei leerem Cache: True (fail-open)
```

**Provider:**
- `anthropic` — Anthropic API direkt
- `openrouter` — OpenRouter (100+ Modelle)
- `openai` — OpenAI API direkt
- `groq` — Groq (schnelle Inference)
- `deepseek` — DeepSeek
- `nvidia` — NVIDIA NIM
- `google` — Google Gemini

**5-Minuten-TTL-Cache:** Live-Fetch wird gecacht damit nicht jeder Request die API bemüht.

---

## media_models.py — Media-SSOT

```python
# TTS-Modelle (Text-to-Speech):
list_speech_models() → live von OpenRouter /models?output_modalities=speech
# Fallback: ["openai/gpt-4o-audio-preview", ...]

# Transcribe-Modelle (Audio → Text):
list_transcribe_models() → live von OpenRouter /models?input_modalities=audio
# Fallback: ["openai/whisper-large-v3", ...]

# Video-Modelle:
list_video_models() → live von OpenRouter /videos/models
# Fallback: ["kling/kling-video-v2-master", "google/veo-3.1", ...]
```

**Bild-Modelle:** Katalog-Modelle (hardcoded Kurz-Liste):
- `openai/gpt-5-image-mini` (default, günstig)
- `openai/gpt-5-image`
- `google/gemini-2.5-flash-image`

**Musik-Modelle:**
- `google/lyria-3-pro-preview` (default)
- `google/lyria-3-clip-preview` (kurze Clips)

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

| Endpoint | Beschreibung |
|---|---|
| `GET /api/llm/models?provider=openrouter` | Live-Modell-Liste eines Providers |
| `GET /api/llm/catalog` | Kompletter Provider-Katalog |
| `GET /api/llm/speech-models` | TTS-Modelle |
| `GET /api/llm/transcribe-models` | Transcribe-Modelle |
| `GET /api/llm/video-models` | Video-Modelle |

---

## Frontend-Nutzung

- `features/llm/MediaModelsSection.tsx` — Video/Transcribe/Speech Modell-Picker
- `features/chat/ModelPicker.tsx` — Modell-Auswahl im Chat (Such-Combobox, 🆓-Badge)
- `features/agents/AgentForm.tsx` — Modell-Auswahl im Agent-Config

**SSOT-Lektion (gelernt):** Früher waren Modell-Listen hardgespiegelt über 6+ Dateien.
Nach dem SSOT-Umbau: Frontend holt Live-Liste von API. Kein Drift mehr.

---

## OpenRouter-Gratis-Modelle

`:free`-Modelle (z.B. `deepseek-v4-flash:free`) können trotz Verfügbarkeit im Katalog
mit 429/404 antworten — das ist OpenRouters Data-Policy (Logging-Zustimmung unter
https://openrouter.ai/settings/privacy nötig für free tier). Kein HH2-Bug.

---

## Verwandte Subsysteme

- **→ Runner** (`01-runner.md`): nutzt `catalog.validate_model()`, `_pricing.cost_micros()`
- **→ Compaction** (`06-compaction.md`): `tokens.context_window_for(model)`
- **→ Multimodal** (`30-multimodal.md`): `media_models.py` ist SSOT für Media-Tools
- **→ OAuth** (`36-oauth.md`): OAuth-Flows für Anthropic/OpenAI
