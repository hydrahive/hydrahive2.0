# LLM & Modelle

Subsystem für alles rund um LLM-Zugriff, Modell-Katalog, Provider-Verwaltung, OAuth-Logins (Anthropic / OpenAI-Codex), Embedding-Modelle, Media-Modelle (image/music/tts/transcribe/video), Pricing/Cost-Tracking, Reasoning-Effort und Usage-/Rate-Limit-Anzeige.

**LLM-SSOT (SP1+SP2, 2026-06-04):** Die Modell-Listen sind auf EINE kanonische Registry (`llm/registry.py`) + EINEN API-Endpoint (`GET /api/llm/models?modality=`) + EINE Config-Sektion (`DefaultModelsSection.tsx`) vereinheitlicht. Alle Picker lesen dieselbe Quelle. Alte Modality-Routen (`/embed-models`/`/speech-models`/`/transcribe-models`/`/video-models`) gelöscht.

Kanonische Quellen:
- Backend Core: `core/src/hydrahive/llm/` + `core/src/hydrahive/oauth/`
- API-Routen: `core/src/hydrahive/api/routes/llm.py`, `llm_catalog.py`, `llm_oauth.py`
- Frontend: `frontend/src/features/llm/`
- Konfig-Datei (SSOT zur Laufzeit): `llm.json` (Pfad via `settings.llm_config`)

---

## WAS

### Kanonische Modell-Registry (`llm/registry.py`)
- `ModelEntry(frozen=True)` — `id`, `provider`, `label`, `purposes: frozenset[str]`, `context_window`, `is_free`, `embed_dim`, `source` (`"live"` | `"fallback"`). `registry.py:26`
- `PURPOSES = ("chat","embed","tts","stt","image","video","music")` — vollständige Zweck-Menge. `registry.py:22`
- `_classify_catalog_entry(entry) -> frozenset[str]` — Default chat; image/music aus `output_modalities`. `registry.py:37`
- `async _build() -> list[ModelEntry]` — aggregiert Chat-Katalog + Embed + TTS/STT/Video; dedupliziert per id, vereinigt Zweck-Mengen. `registry.py:81`
- `async list_models(modality?) -> list[ModelEntry]` — gecacht (TTL=300s), leere Liste wird NICHT gecacht (nächster Call retryt). Double-Check-Lock. `registry.py:122`
- `known_ids() -> set[str]` — sync, aus Cache (kein Fetch). Für `validate_model`. `registry.py:144`
- `is_known(model_id) -> bool` — True wenn bekannt ODER Cache leer (fail-open). `registry.py:149`
- `async awarm()` — Lifespan-Startup-Vorwärmung; blockiert nicht. `registry.py:155`
- `invalidate()` — Cache leeren + Lock resetten (nach `PUT /api/llm`). `registry.py:163`
- `_CACHE_TTL = 300.0`, `_cache: tuple[float, list[ModelEntry]] | None`, `_lock: asyncio.Lock`. `registry.py:52-54`

### LLM-Client Public-API (`llm/client.py`)
- `default_model()` — liefert `default_model` aus `llm.json`. `llm/client.py:59`
- `complete(messages, model?, temperature=0.7, max_tokens=4096) -> str` — ein nicht-streamender Call, Routing nach Provider. `llm/client.py:63`
- `stream(messages, model?, temperature=0.7, max_tokens=4096) -> AsyncIterator[str]` — Streaming-Variante, gleiche Routing-Logik. `llm/client.py:110`
- Re-Export-Aliase (Backwards-Compat für `runner/`, `voice/tts.py`, `agents/_validation.py`): `_load_config`, `_apply_keys`, `_strip_provider_prefix`, `_ENV_MAP`, `_ANTHROPIC_OAUTH_HEADERS`, `_ANTHROPIC_OAUTH_IDENTITY`, `MINIMAX_BASE_URL`. `llm/client.py:36-42`
- `_get_anthropic_key(cfg)` / `_get_minimax_key(cfg)` — dünne Wrapper um `get_provider_key`. `llm/client.py:45-50`
- `__all__` exportiert nur `complete, stream, default_model, is_minimax_model, convert_images_for_minimax`. `llm/client.py:53`

### Routing-Pfade (im `complete`/`stream` und `runner/llm_bridge.py`)
- MiniMax-Modelle → anthropic-SDK gegen `api.minimax.io/anthropic`.
- `claude-*`-Modelle → anthropic-SDK direkt (OAuth-Token bevorzugt, sonst Plain-Bearer-API-Key).
- `openai-codex/*`-Modelle → ChatGPT-Plus/Pro-Backend via Codex-OAuth (Responses-API).
- Alle anderen (OpenAI mit API-Key, OpenRouter, Groq, Mistral, Gemini, NVIDIA NIM) → LiteLLM.

### Config-Loading & Provider-Keys (`llm/_config.py`)
- `_ENV_MAP` — Provider-ID → ENV-Variablenname für LiteLLM (`anthropic`→`ANTHROPIC_API_KEY`, …, `nvidia`→`NVIDIA_NIM_API_KEY`). `llm/_config.py:9-17`
- `provider_env_vars() -> set[str]` — SSOT der ENV-Variablennamen; wird von der shell_exec-Denylist konsumiert. `llm/_config.py:19`
- `load_config() -> dict` — mtime-gecachtes Lesen von `llm.json`, Default `{"providers": [], "default_model": ""}`. `llm/_config.py:29`
- `apply_keys(config)` — setzt Provider-API-Keys als ENV-Vars (nur LiteLLM-Pfad). `llm/_config.py:45`
- `get_provider_key(config, provider_id) -> str` — API-Key eines Providers. `llm/_config.py:57`
- `openrouter_key() -> str` — SSOT für OpenRouter-Key (alle Media-Tools). `llm/_config.py:64`
- `get_provider_group_id(config, provider_id) -> str` — MiniMax-`group_id` (für Embeddings). `llm/_config.py:69`
- `_config_cache: tuple[float, dict] | None` — mtime-Cache-Slot. `llm/_config.py:26`
- `_PURPOSE_KEYS: dict[str, tuple[str, ...]]` — SSOT-Mapping Zweck → Pfad in `llm.json` (z.B. `"stt"` → `("media_models","transcribe")`; `"chat"` → `("default_model",)`). `llm/_config.py:77`
- `get_default(purpose) -> str` — liest konfigurierten Default via `_PURPOSE_KEYS` aus `load_config()`. `llm/_config.py:88`
- `set_default(purpose, model)` — schreibt `llm.json` + invalidiert `_config_cache`. `llm/_config.py:97`

### Anthropic-/MiniMax-Direkt-SDK-Pfad (`llm/_anthropic.py`)
- `_OAUTH_HEADERS` — Claude-Code-Identität-Header (`anthropic-beta` mit `claude-code-20250219,oauth-2025-04-20,fine-grained-tool-streaming-2025-05-14,prompt-caching-2024-07-31`, `user-agent: claude-cli/2.1.62`, `x-app: cli`). `llm/_anthropic.py:12`
- `_OAUTH_IDENTITY` — Pflicht-System-Text bei OAuth ("You are Claude Code, …"). `llm/_anthropic.py:18`
- `MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"` (Global Platform; NICHT china `minimaxi.com`). `llm/_anthropic.py:23`
- `EFFORT_LEVELS = ("low","medium","high","xhigh","max")` — gültige Effort-Stufen für den neuen `output_config.effort`-Pfad. `llm/_anthropic.py:26`
- `EFFORT_PARAM_MODELS = ("claude-opus-4-6","claude-opus-4-7","claude-opus-4-8","claude-sonnet-4-6")` — Modelle mit adaptive-thinking + `output_config.effort`. `llm/_anthropic.py:30`
- `EFFORT_TO_BUDGET = {"low":1024,"medium":4096,"high":16384}` — Legacy-Mapping Effort → `budget_tokens`. `llm/_anthropic.py:36`
- `_uses_effort_param(model) -> bool` — True für Claude 4.6+. `llm/_anthropic.py:39`
- `apply_effort(kwargs, model, effort)` — mutiert kwargs in-place: neuer Pfad (`thinking={"type":"adaptive"}` + `output_config.effort`) oder Legacy (`thinking enabled budget_tokens`, `temperature=1.0`, `max_tokens` hochgezogen). `llm/_anthropic.py:45`
- `strip_provider_prefix(model)` — entfernt `anthropic/`/`minimax/`-Prefix. `llm/_anthropic.py:74`
- `extract_text(content)` — joined Text-Blocks, skippt ThinkingBlocks. `llm/_anthropic.py:82`
- `is_minimax_model(model) -> bool`. `llm/_anthropic.py:89`
- `convert_images_for_minimax(messages)` — Anthropic-Image-Blocks → OpenAI `image_url`-Blocks (MiniMax-Workaround). `llm/_anthropic.py:95`
- `_client(key) -> (AsyncAnthropic, is_oauth)` — OAuth (`sk-ant-oat`) bekommt `auth_token`+Identity-Header, Plain bekommt `api_key`. `llm/_anthropic.py:122`
- `anthropic_complete(...)` — non-stream; extrahiert `role=system` als top-level `system`; bei OAuth überschreibt `_OAUTH_IDENTITY`; nutzt `with_raw_response` um Rate-Limit-Header zu extrahieren. `llm/_anthropic.py:134`
- `minimax_complete(...)` / `minimax_stream(...)` — eigener Client gegen `MINIMAX_BASE_URL` mit `Authorization: Bearer`-Header, 60s-Timeout. `llm/_anthropic.py:160`, `:180`
- `anthropic_stream(...)` — Streaming. `llm/_anthropic.py:201`

### Modell-Katalog — Logik (`llm/catalog.py`)
- `_CACHE_TTL = 300` (5-Min), `_cache`, `_cache_locks`. `llm/catalog.py:31-33`
- `_cache_clear()`. `llm/catalog.py:36`
- `_cached_fetch(provider_id, api_key)` — Live-Fetch mit TTL-Cache + Per-Provider-Lock (Double-Check nach Lock); cached nur erfolgreiche Fetches. `llm/catalog.py:40`
- `_normalize_id(provider_id, raw_id)` — fügt Provider-Prefix hinzu (`meta/llama-…` → `nvidia_nim/meta/llama-…`). `llm/catalog.py:57`
- `_parse_models_response(provider_id, data)` — extrahiert id/context_window/pricing/is_free/modalities; OpenRouter liefert pricing-Strings, Gemini liefert `models[].name`. `is_free` = beide Preise `"0"`, sonst None wenn kein Pricing. `llm/catalog.py:65`
- `_auth_for(cfg, api_key) -> (headers, params)` — `bearer` | `query` (`?key=`) | `x-api-key` (Anthropic, + `anthropic-version`). `llm/catalog.py:105`
- `_fetch_live_models(provider_id, api_key)` — httpx GET, 15s-Timeout, bei Fehler `[]`. `llm/catalog.py:117`
- `_enrich(provider_id, entry)` — joint Live-Eintrag mit `METADATA` (Live-context_window hat Vorrang), setzt `supports_effort` via `_uses_effort_param`, `unknown` = nicht in METADATA. `llm/catalog.py:135`
- `catalog_for_providers(providers) -> list[dict]` — pro Provider parallel; bei leerem Live-Fetch Fallback auf `STATIC_MODELS`; liefert `{provider_id, provider_name, configured, models, live_count}`. `llm/catalog.py:155`

### Katalog-Statik-Daten (`llm/_catalog_data.py`)
- `PROVIDER_ENDPOINTS` — pro Provider `{url, auth, query_param?}` zum Live-Listing. OpenAI/NVIDIA/Groq/Mistral/OpenRouter = bearer, Gemini = query, Anthropic = x-api-key; MiniMax + OpenAI-Codex = `url:None` (kein public `/v1/models`). `_catalog_data.py:13`
- `STATIC_MODELS` — Fallback-Listen für `anthropic` (7 Claude-IDs), `minimax` (10 IDs inkl. `embo-01`), `openai-codex` (9 IDs). `_catalog_data.py:28`
- `PROVIDER_PREFIX` — LiteLLM-Prefixe (`openai/`, `nvidia_nim/`, `groq/`, `mistral/`, `openrouter/`, `gemini/`). `_catalog_data.py:52`
- `METADATA` — große interne Tabelle (Modell-ID → `context_window`, `tool_use`, `category`, `family`, optional `params`). ~190 Einträge: Anthropic, MiniMax, NVIDIA NIM (Llama/Qwen/Mistral/Gemma/Phi/Granite/DeepSeek/Kimi/GPT-OSS/Nemotron/…), OpenAI (`gpt-5`, `gpt-4o`, `o1`), OpenAI-Codex (`gpt-5.1…gpt-5.5`). `_catalog_data.py:59`

### Embedding-Modelle (`llm/embed.py`)
- `EMBED_MODELS` — Lookup-Table pro Provider mit `{model, litellm, dim, api_base?}`. Provider: openai (3), nvidia (2, api_base), minimax (1, api_base, `embo-01`), mistral (1), gemini (1), cohere (2), openrouter (1, `baai/bge-m3-20251117` dim 1024, api_base). `llm/embed.py:16`
- `_PROVIDER_BY_MODEL`, `_BY_MODEL` — Reverse-Indizes. `llm/embed.py:68`, `:74`
- `dim_for_model(model) -> int` — Dimension (0 wenn unbekannt). `llm/embed.py:81`
- `litellm_model(model) -> str` — LiteLLM-String. `llm/embed.py:85`
- `available_for_config(config) -> list[dict]` — Embed-Modelle für die ein Key konfiguriert ist; `{model, dim, provider}`. `llm/embed.py:89`
- `aembed(text, model, embed_type="db") -> list[float] | None`. `llm/embed.py:104`
- `aembed_batch(texts, model, embed_type="db", _retry=3)` — Batch-Embedding; api_base-Provider via openai-Client (NVIDIA mit `input_type` query/passage), MiniMax via eigenem httpx-Call (`type`-Param + optional `GroupId`), sonst LiteLLM. Rate-Limit-Retry (60s × attempt). `llm/embed.py:115`
- `_is_rate_limit(e)` — String-Heuristik. `llm/embed.py:110`

### Media-Modelle (`llm/media_models.py`)
- `DEFAULTS` — Fallback-Modell pro Kategorie: image=`openai/gpt-5-image-mini`, music=`google/lyria-3-pro-preview`, tts=`hexgrad/kokoro-82m`, transcribe=`openai/whisper-large-v3`, video=`kling/kling-video-v2-master`. `media_models.py:32`
- `_CATEGORY_MODALITY` — image=(output,image), music=(output,audio), transcribe=(input,audio); tts+video laufen über eigene Endpoints. `media_models.py:43`
- `get_media_model(category, config?) -> str` — aktives Modell, liest `media_models[category]`, Fallback DEFAULTS, strippt führendes `openrouter/`. `media_models.py:69`
- `candidates(category, catalog_entries)` — filtert Katalog nach Modalität. `media_models.py:86`
- `list_speech_models(force=False)` — Live-TTS-Modelle (`?output_modalities=speech`) inkl. `supported_voices`; 5-Min-Cache; ohne Key `[]`. `media_models.py:96`
- `voices_for(model)` / `first_voice(model)`. `media_models.py:122`, `:130`
- `_TRANSCRIBE_FALLBACK` — 3 Whisper-IDs. `media_models.py:138`
- `list_transcribe_models(force=False)` — versucht `?input_modalities=audio`, fällt bei leerem Ergebnis auf Fallback zurück (OpenRouter-Filter unzuverlässig). `media_models.py:145`
- `list_video_models(force=False)` — `/api/v1/videos/models` (eigene Fläche), 5-Min-Cache. `media_models.py:181`
- Cache-Slots + `_speech_cache_clear`/`_transcribe_cache_clear`/`_video_cache_clear`. `media_models.py:49-66`

### Pricing / Cost-Tracking (`llm/_pricing.py`)
- `Pricing(NamedTuple)` — `input, output, cache_read, cache_creation` in Mikro-Cents/Token. `_pricing.py:15`
- Tabellen `_ANTHROPIC` (Sonnet/Opus/Haiku 4.x + 3.7/3.5), `_OPENAI` (gpt-5/4o/4o-mini/4-turbo), `_DEEPSEEK`, `_GEMINI`. `_pricing.py:25-61`
- `provider_from_model(model) -> str` — Heuristik aus Modell-Name. `_pricing.py:64`
- `_match(model, table)` — Prefix-Match, längster Prefix gewinnt. `_pricing.py:87`
- `lookup(provider, model) -> Pricing | None` — OpenRouter explizit `None` (Tokens gezählt, Kosten NULL). `_pricing.py:97`
- `cost_micros(provider, model, *, prompt_tokens, completion_tokens, cache_read_tokens, cache_creation_tokens) -> int | None` — summiert 4 Buckets. `_pricing.py:113`

### MiniMax-Quota (`llm/_minimax_usage.py`)
- `fetch_usage() -> dict` — `GET /v1/token_plan/remains`, 30s-Cache; bei no-key/Fehler `{available:False, reason}`. `_minimax_usage.py:79`
- `_MODEL_CATEGORIES` — Klassifizierung (m2=text/5h/Requests, hailuo=video, speech=tts, music, image). `_minimax_usage.py:26`
- `_classify`, `_normalize_model` (interval/weekly total/used/pct/reset). `_minimax_usage.py:35`, `:48`

### Anthropic OAuth-Usage / Rate-Limits (`llm/_oauth_usage.py`)
- `_CACHE_FILE = data_dir/oauth_usage.json`, `_oauth_rate_limits` global. `_oauth_usage.py:22-24`
- `extract_rate_limit_headers(headers)` — parst `anthropic-ratelimit-unified-*` (status, 5h/7d utilization+reset+threshold, overage-*), persistiert. `_oauth_usage.py:46`
- `get_oauth_rate_limits() -> dict`. `_oauth_usage.py:111`
- `_load_cache`/`_save_cache`; beim Import wird Cache geladen. `_oauth_usage.py:27`, `:37`, `:117`

### OAuth-Provider (`oauth/`)
- `_base.py`: `REFRESH_THRESHOLD_S=300`, `b64url`, `make_pkce() -> (verifier, challenge)` (S256), `make_state()`. `oauth/_base.py:9-25`
- `anthropic.py`: Login mit Claude Pro/Max. `CLIENT_ID`, `AUTHORIZE_URL` (claude.ai), `TOKEN_URL` (platform.claude.com), `REDIRECT_URI` (localhost:53692), `SCOPES`, `_HTTP_HEADERS` (claude-cli-UA gegen Cloudflare). Funktionen: `authorize_url`, `parse_callback_input`, `exchange_code`, `refresh_access_token`, `_normalize_token_response`, `resolve_anthropic_token()`. `oauth/anthropic.py`
- `openai_codex.py`: Login mit ChatGPT Plus/Pro. `CLIENT_ID`, `AUTHORIZE_URL`/`TOKEN_URL` (auth.openai.com), `REDIRECT_URI` (localhost:1455/auth/callback), `SCOPE`, `ORIGINATOR="hydrahive"`. Funktionen: `authorize_url`, `parse_callback_input`, `extract_account_id` (JWT-Decode), `exchange_code` (form-urlencoded), `refresh_access_token`, `_normalize_token_response`, `CODEX_PROVIDER_ID`, `resolve_openai_codex_token()`. `oauth/openai_codex.py`
- `_llm_config_rmw.py`: `update_provider_oauth(path, provider_id, new_oauth_block)` — atomic RMW mit `fcntl.flock` auf `<llm.json>.lock`, temp+rename. `_atomic_write`. `oauth/_llm_config_rmw.py:28`, `:34`

### API-Endpoints — `routes/llm.py` (prefix `/api/llm`)
- `GET /api/llm` (admin) — `get_config()`, ganze `llm.json` inkl. OAuth-Blöcke. `routes/llm.py:53`
- `PUT /api/llm` (admin) — `update_config(cfg: LlmConfig)`, speichert, ruft `registry.invalidate()`, triggert bei `embed_model`-Wechsel `mirror.on_embed_model_change`. `routes/llm.py:58`
- `POST /api/llm/test` (admin) — `test_connection(model?)`, 1-Wort-Call. `routes/llm.py:76`
- `GET /api/llm/minimax/usage` (auth) — MiniMax-Quota. `routes/llm.py:89`
- `GET /api/llm/anthropic/rate-limits` (auth) — OAuth-Rate-Limits. `routes/llm.py:95`
- `GET /api/llm/effort-models` (auth) — `{prefixes: EFFORT_PARAM_MODELS}`, SSOT fürs Frontend (#214). `routes/llm.py:101`
- **`GET /api/llm/models?modality=` (auth)** — kanonische Modell-Liste aus Registry, gefiltert nach Zweck. Liefert `{models: [ModelEntry], default: str}`. Für ALLE Picker (require_auth, nicht admin-only). `default` = konfiguriertes Standardmodell des Zwecks via `_config.get_default`. `routes/llm.py:112`
- ~~`GET /api/llm/embed-models`~~ **GELÖSCHT** (SP1)
- ~~`GET /api/llm/speech-models`~~ **GELÖSCHT** (SP1)
- ~~`GET /api/llm/transcribe-models`~~ **GELÖSCHT** (SP1)
- ~~`GET /api/llm/video-models`~~ **GELÖSCHT** (SP1)
- Pydantic-Modelle: `LlmProvider` (`extra="allow"` für OAuth-Block!), `LlmConfig` (providers/default_model/embed_model/media_models), `TestRequest`. `routes/llm.py:23`, `:33`, `:72`
- `_load()`/`_save()` — direkter `llm.json`-Zugriff. `routes/llm.py:42`, `:48`

### API-Endpoints — `routes/llm_catalog.py` (prefix `/api/llm/catalog`)
- `GET /api/llm/catalog` (admin) — `get_catalog()`, Live-Listing aller Provider. `routes/llm_catalog.py:19`
- `POST /api/llm/catalog/test` (admin) — `test_model(model)`, `{ok, latency_ms, response/error}`. `routes/llm_catalog.py:32`
- `POST /api/llm/catalog/use-in-agent` (admin) — `use_in_agent(agent_id, model)`, setzt `agent.llm_model`, trägt Modell in Provider-Liste ein. `routes/llm_catalog.py:102`
- `_ensure_model_in_providers(model)` — ordnet Modell per Prefix dem Provider zu, ergänzt `provider.models`. `routes/llm_catalog.py:61`

### API-Endpoints — `routes/llm_oauth.py` (prefix `/api/llm/oauth`)
- `POST /api/llm/oauth/start` (admin) — `oauth_start(provider)`, NUR `openai-codex`; PKCE+State in pending-File, liefert `authorize_url`. `routes/llm_oauth.py:101`
- `POST /api/llm/oauth/exchange` (admin) — `oauth_exchange(provider, code_or_url)`, NUR `openai-codex`; TTL-Check (600s), State-Match, Token-Tausch, schreibt OAuth-Block. `routes/llm_oauth.py:118`
- `DELETE /api/llm/oauth/{provider}` (admin) — `oauth_revoke`, NUR `openai-codex`, entfernt `oauth`-Feld. `routes/llm_oauth.py:157`
- `CODEX_DEFAULT_MODELS` (9 IDs), `PENDING_TTL_SECONDS=600`. `routes/llm_oauth.py:30`, `:28`
- Helpers: `_load_pending`/`_save_pending`(chmod 0600)/`_delete_pending`/`_write_provider_oauth`. `routes/llm_oauth.py:62-98`

### Frontend — Feature-Folder `features/llm/`
- `api.ts` — Typen (`LlmProvider`, `LlmConfig`, `OAuthBlock`, `AnthropicRateLimits`, `CatalogModel`, `CatalogProvider`, `CatalogTestResult`, **`RegistryModel`**) + Clients `llmApi` (getConfig/updateConfig/testConnection/oauthStart/oauthExchange/oauthRevoke/getAnthropicRateLimits) + `catalogApi` (get/test/useInAgent) + **`llmModelsApi.byModality(modality?)`** (`GET /llm/models?modality=`, liefert `{models: RegistryModel[], default: string}`). `features/llm/api.ts:96-109`
- `LlmPage.tsx` — Hauptseite: Provider-Liste, `DefaultModelsSection`, Test-Button, Anthropic-Usage-Card. `features/llm/LlmPage.tsx:10,121`
- **`DefaultModelsSection.tsx`** — **neue einheitliche Config-Sektion** für alle 7 Zwecke (chat/embed/image/music/tts/stt/video). Holt per Zweck via `llmModelsApi.byModality`, speichert direkt via `llmApi.updateConfig`. Löst `MediaModelsSection.tsx` ab. `features/llm/DefaultModelsSection.tsx:1-148`
- `CatalogPage.tsx` — Modell-Katalog (Admin): Provider-Tabs, Suche, Filter, Test, "Im Agent nutzen". `features/llm/CatalogPage.tsx`
- `ProviderForm.tsx` — Provider hinzufügen/editieren; OAuth-Branch; MiniMax `group_id`. `features/llm/ProviderForm.tsx`
- `ProviderCard.tsx` — Provider-Anzeige (OAuth-Badge, masked Key, Revoke-Button). `features/llm/ProviderCard.tsx`
- `OAuthFlow.tsx` — 2-Schritt-OAuth-UI (Login öffnen → URL/Code einfügen). `features/llm/OAuthFlow.tsx`
- ~~`MediaModelsSection.tsx`~~ — **GELÖSCHT** (SP1); ersetzt durch `DefaultModelsSection.tsx`.
- `AnthropicUsageCard.tsx` — 5h/7d-Utilization + Reset + Overage; 60s-Polling. `features/llm/AnthropicUsageCard.tsx`
- `effort.ts` — `fetchEffortPrefixes`/`useEffortPrefixes`/`modelSupportsExtendedEffort`. `features/llm/effort.ts`
- `_llm_providers.ts` — `KNOWN_PROVIDERS` (9: anthropic/openai/openai-codex(oauth)/openrouter/groq/mistral/gemini/minimax/nvidia). `features/llm/_llm_providers.ts`

**Picker-Konsumenten außerhalb `features/llm/`** (alle via `llmModelsApi.byModality("chat")`):
- `features/chat/ModelPicker.tsx:2,29`
- `features/chat/commands.ts:7,42,47`
- `features/agents/AgentsPage.tsx:9,32`
- `features/buddy/BuddySettingsPage.tsx:6,38`
- `features/projects/NewProjectDialog.tsx:5,28`

---

## WIE

### Provider anlegen (LLM-Seite)
1. `LlmPage` lädt `GET /api/llm` (Config); `DefaultModelsSection` lädt Modell-Listen per Zweck via `llmModelsApi.byModality`. `LlmPage.tsx:10,121`
2. "+" öffnet `ProviderForm`. Bei Auswahl eines OAuth-Providers (`openai-codex`) wird statt API-Key-Feld die `OAuthFlow`-Komponente gezeigt.
3. Save → `addProvider`/`updateProvider` → `save(next)` → `PUT /api/llm` → Backend `update_config` schreibt `llm.json`, ruft `registry.invalidate()`. `routes/llm.py:58-69`
4. `update_config` vergleicht alten vs neuen `embed_model`; bei Änderung `await mirror.on_embed_model_change(new_model)`. `routes/llm.py:60-68`

### LLM-Call (Agent-Runner-Pfad)
1. Runner liest `reasoning_effort` aus `session.metadata`. `runner/runner.py:170`
2. `call_with_tools(model, system_prompt, …, reasoning_effort)` (`runner/llm_bridge.py:13`):
   - `cfg = _load_config()`; `target = model or default_model`.
   - MiniMax → `minimax_anthropic_call` (`_llm_bridge_backends`), kwargs via `build_minimax_kwargs` (cache_control entfernt, system als EIN String). `runner/_anthropic_payload.py:137`
   - `claude-*` → `resolve_anthropic_token()` (refresht falls nötig) → `anthropic_call`, kwargs via `build_anthropic_kwargs` (delikate Cache-Ordering: OAuth-Identity zuerst, system+summary mit `cache_control`, volatile OHNE, Breakpoint auf letzter Message/letztem Tool; `apply_effort`). `runner/_anthropic_payload.py:83-134`
   - `openai-codex/*` → `resolve_openai_codex_token()` → `codex_call` (chatgpt.com Responses-API, Header `chatgpt-account-id`). `runner/_codex_provider.py`
   - sonst → `apply_keys(cfg)` + `litellm_call`.
3. Anthropic-Calls extrahieren Rate-Limit-Header über `with_raw_response` → `extract_rate_limit_headers` → persistiert `oauth_usage.json`.
4. Runner schreibt pro Call eine `llm_calls`-Zeile inkl. `cost_micros(provider_from_model(model), …)`. `runner/runner.py:209-238`

### Reasoning-Effort-Zustandsmaschine (`apply_effort`)
- effort leer/None → no-op.
- Claude 4.6+ (`_uses_effort_param`): effort muss in `EFFORT_LEVELS` sein → `thinking={"type":"adaptive"}` + `output_config.effort=<level>`. temperature/max_tokens unangetastet.
- Legacy (Claude 4.5/älter, MiniMax): nur low/medium/high → `EFFORT_TO_BUDGET` → `thinking enabled budget_tokens`, `max_tokens` mind. `budget+4096`, `temperature=1.0`.
- Frontend spiegelt das: `/llm/effort-models` liefert `EFFORT_PARAM_MODELS`; `modelSupportsExtendedEffort` entscheidet, ob xhigh/max anboten werden.

### Modell-Katalog (Live-Listing)
1. `CatalogPage` → `catalogApi.get()` → `GET /api/llm/catalog`.
2. `catalog_for_providers(providers)` ruft pro Provider `_cached_fetch` parallel. `catalog.py:155`
3. `_cached_fetch`: TTL-Cache (300s) + Per-Provider-`asyncio.Lock` (Double-Check). Bei Miss `_fetch_live_models` → httpx gegen `PROVIDER_ENDPOINTS[pid].url` mit `_auth_for`. `catalog.py:40`, `:117`
4. `_parse_models_response` extrahiert id/context_window/pricing/modalities. `catalog.py:65`
5. Leerer Live-Fetch → Fallback `STATIC_MODELS` (für minimax/openai-codex immer; für andere nur bei Fetch-Fehler). `catalog.py:164`
6. `_enrich` joint mit `METADATA`, setzt `supports_effort`/`unknown`. `catalog.py:135`
7. "Im Agent nutzen": `POST /api/llm/catalog/use-in-agent` → `_ensure_model_in_providers` (Modell in Provider-Liste) → `agent_config.update(llm_model=…)` (durch `validate_model`). `routes/llm_catalog.py:102`

### validate_model-Interaktion
- `_available_models()` liest **`registry.known_ids()`** (sync, aus Cache). `agents/_validation.py:45-49`
- `validate_model`: leere Menge → durchwinken (Erst-Setup/Fetch-Fehler/Cache kalt); sonst muss Modell drin sein. `agents/_validation.py:52-61`
- Fix (SP1): vorher las `_available_models` direkt aus `catalog._cache` — das schloss statische Fallback-Modelle (z.B. claude bei 401-Auth) aus. Registry aggregiert Fallbacks, deshalb tauchen sie jetzt auf.
- `use-in-agent` trägt Modell weiterhin aktiv in Provider-Liste ein, damit `validate_model` auch ohne warmen Cache nicht blockt.

### OpenAI-Codex-OAuth (GUI-Flow)
1. `OAuthFlow` → `oauthStart("openai-codex")` → `POST /api/llm/oauth/start`: `make_pkce`+`make_state`, pending-File (chmod 0600, ts), liefert `authorize_url`. `routes/llm_oauth.py:101`
2. Browser öffnet auth.openai.com; redirect zu `localhost:1455/auth/callback` (Connection-Refused-Page) — User kopiert URL.
3. `oauthExchange` → `POST /api/llm/oauth/exchange`: pending laden, TTL/State prüfen, `parse_callback_input` → code, `exchange_code` (form-urlencoded) → Token, `_write_provider_oauth` (Provider `openai-codex` anlegen falls fehlt, `default_model` setzen falls leer), pending löschen. `routes/llm_oauth.py:118`
4. Token-Refresh bei Bedarf: `resolve_openai_codex_token` prüft `expires_at`, refresht (`refresh_access_token`), schreibt via `update_provider_oauth` (flock). `oauth/openai_codex.py:168`

### Anthropic-OAuth (Token-Auflösung)
- `resolve_anthropic_token` liest `llm.json` Provider `anthropic`: OAuth-Block bevorzugt; gültig → access; ablaufend → `refresh_access_token` → `update_provider_oauth`; kein OAuth → `api_key`. Bei Refresh-Fehler → alten access zurück. `oauth/anthropic.py:156`
- HINWEIS: Es gibt KEINEN GUI-Flow für Anthropic-OAuth (siehe Offene Enden). Die Funktionen `authorize_url`/`exchange_code` existieren, sind aber an keine Route gebunden.

### Embedding-Backfill bei Modell-Wechsel
- `PUT /api/llm` mit neuem `embed_model` → `mirror.on_embed_model_change(new_model)`: `_cancel_backfill`, `ensure_embed_col` für `events`+`cards`, dann `_start_backfill(new_model)`. `db/mirror.py:102`

---

## WO

Backend Core:
- `core/src/hydrahive/llm/__init__.py` — leeres Package-Init.
- **`core/src/hydrahive/llm/registry.py:1-167`** — kanonische Registry: `ModelEntry`, `_classify_catalog_entry`, `_build`, `list_models`, `known_ids`, `is_known`, `awarm`, `invalidate`.
- `core/src/hydrahive/llm/client.py:59-163` — `default_model`/`complete`/`stream` + Re-Exports.
- `core/src/hydrahive/llm/_config.py:9-111` — `_ENV_MAP`, `load_config`, `apply_keys`, `get_provider_key`, `openrouter_key`, `get_provider_group_id`, `provider_env_vars`, **`_PURPOSE_KEYS`**, **`get_default`**, **`set_default`**.
- `core/src/hydrahive/llm/_anthropic.py:12-217` — Direkt-SDK, Effort-Konstanten+`apply_effort`, MiniMax-Helpers.
- `core/src/hydrahive/llm/catalog.py:31-177` — Katalog-Logik + Cache (jetzt intern via Registry).
- `core/src/hydrahive/llm/_catalog_data.py:13-249` — `PROVIDER_ENDPOINTS`/`STATIC_MODELS`/`PROVIDER_PREFIX`/`METADATA`.
- `core/src/hydrahive/llm/embed.py:16-182` — Embedding-Modelle + `aembed_batch` (intern via Registry).
- `core/src/hydrahive/llm/media_models.py:32-207` — Media-Modell-Resolver + Live-Listen (intern via Registry).
- `core/src/hydrahive/llm/_pricing.py:15-135` — Pricing-Tabellen + `cost_micros`.
- `core/src/hydrahive/llm/_minimax_usage.py:79-114` — `fetch_usage`.
- `core/src/hydrahive/llm/_oauth_usage.py:46-117` — Rate-Limit-Header-Cache.
- `core/src/hydrahive/oauth/_base.py:9-25` — PKCE/State.
- `core/src/hydrahive/oauth/anthropic.py:29-205` — Anthropic-OAuth-Konstanten + Flow + `resolve_anthropic_token`.
- `core/src/hydrahive/oauth/openai_codex.py:32-208` — Codex-OAuth-Konstanten + Flow + `resolve_openai_codex_token` + `extract_account_id`.
- `core/src/hydrahive/oauth/_llm_config_rmw.py:28-63` — flock-RMW.

API-Routen (registriert in `core/src/hydrahive/api/main.py`):
- `core/src/hydrahive/api/routes/llm.py:1-137` — prefix `/api/llm`.
- `core/src/hydrahive/api/routes/llm_catalog.py:16-119` — prefix `/api/llm/catalog`.
- `core/src/hydrahive/api/routes/llm_oauth.py:25-170` — prefix `/api/llm/oauth`.

Lifespan:
- `core/src/hydrahive/api/lifespan.py:124-127` — `asyncio.create_task(llm_registry.awarm())` beim Start; Registry-Invalidierung bei `PUT /api/llm` via `routes/llm.py:64`.

Cross-Module-Konsumenten:
- `core/src/hydrahive/runner/llm_bridge.py:13-107` — `call_with_tools`, Provider-Routing.
- `core/src/hydrahive/runner/llm_bridge_stream.py:92` — `resolve_anthropic_token` (Stream).
- `core/src/hydrahive/runner/_anthropic_payload.py:83-165` — `build_anthropic_kwargs`/`build_minimax_kwargs` + `apply_effort`.
- `core/src/hydrahive/runner/_codex_provider.py:22,57-64` — `CODEX_URL`, `_headers` (`chatgpt-account-id`).
- `core/src/hydrahive/runner/runner.py:22,211,228` — `cost_micros`, `provider_from_model`, `llm_calls`-Insert.
- `core/src/hydrahive/agents/_validation.py:45-49` — `_available_models` liest **`registry.known_ids()`** (nicht mehr `catalog._cache`).
- `core/src/hydrahive/tools/shell.py:102-104` — `provider_env_vars()` in Denylist.
- `core/src/hydrahive/tools/generate_image.py`, `generate_video.py`, `generate_music.py`, `generate_speech.py`, `transcribe_audio.py`, `_openrouter_media.py`, `_openrouter_transcribe.py` — `get_media_model`/`openrouter_key`.
- `core/src/hydrahive/voice/tts.py`, `api/routes/tts.py` — `get_media_model`.
- `core/src/hydrahive/db/mirror.py:102-112` — `on_embed_model_change`; `db/_mirror_embed.py`/`_mirror_cards.py`/`_mirror_search.py`/`cards/consolidate.py` — `aembed`/`aembed_batch`.

Settings-Pfade:
- `core/src/hydrahive/settings/_paths.py:65` — `oauth_pending_path = data_dir/oauth_pending.json`.
- `core/src/hydrahive/settings/_paths.py:87` — `llm_config = config_dir/llm.json`.
- `oauth_usage.json` Pfad hartkodiert in `llm/_oauth_usage.py:22` (`data_dir/oauth_usage.json`).

Frontend:
- `frontend/src/features/llm/api.ts` — `llmApi`, `catalogApi`, **`llmModelsApi`** (`byModality`), `RegistryModel`.
- `frontend/src/features/llm/LlmPage.tsx`, `CatalogPage.tsx`, `ProviderForm.tsx`, `ProviderCard.tsx`, `OAuthFlow.tsx`, **`DefaultModelsSection.tsx`**, `AnthropicUsageCard.tsx`, `effort.ts`, `_llm_providers.ts`.
- ~~`frontend/src/features/llm/MediaModelsSection.tsx`~~ **GELÖSCHT** (SP1).
- Picker-Konsumenten: `features/chat/ModelPicker.tsx`, `features/chat/commands.ts`, `features/agents/AgentsPage.tsx`, `features/buddy/BuddySettingsPage.tsx`, `features/projects/NewProjectDialog.tsx`.
- Effort-Konsumenten: `frontend/src/features/chat/SessionModelControls.tsx`, `frontend/src/features/buddy/BuddyPage.tsx`.
- MiniMax-Usage-Card: `frontend/src/features/system/MinimaxUsageCard.tsx`.
- i18n-Namespace: `frontend/src/i18n/locales/{de,en}/llm.json`.

Tests (neu in SP1/SP2):
- `core/tests/test_registry_build.py`, `test_registry_classify.py`, `test_registry_invalidate.py` — Registry-Unit-Tests.
- `core/tests/test_validate_registry.py`, `test_validate_model_live.py` — validate_model über Registry.
- `core/tests/test_llm_models_endpoint.py`, `test_llm_models_default.py` — `/api/llm/models`-Endpoint.
- Bestehend: `core/tests/test_embed.py`, `test_media_models.py`, `test_llm_media_models_config.py`, `test_openrouter_media.py`, `test_llm_config_rmw.py`, `test_llm_pricing.py`, `test_catalog_live.py`, `test_llm_calls_logging.py`, `test_anthropic_oauth_headers.py`.

---

## WARUM (nicht-offensichtliche Verdrahtung, Invarianten, Gotchas)

- **Registry als SSOT (SP1+SP2).** `registry.py` ist die einzige Stelle, die alle Modell-Listen zusammenführt. Chat-Katalog, Embed, TTS/STT/Video werden intern aggregiert — kein Konsument greift noch direkt auf `catalog._cache`, `embed.available_for_config` oder `media_models.list_*` für Picker-Zwecke. Wer eine neue Modell-Kategorie hinzufügt, muss sie in `_build()` einklinken. `registry.py:81-119`
- **Leere Registry-Build wird nicht gecacht.** Wenn alle Provider-Fetches fehlschlagen (kein Netz, keine Keys), gibt `_build` eine leere Liste zurück; `list_models` cached das nicht und setzt `_cache=None`. Nächster Aufruf (z.B. beim nächsten Picker-Refresh) retryt. Konsequenz: `known_ids()` gibt leere Menge → `is_known` gibt True → `validate_model` winkt durch. `registry.py:130-133`
- **Startup: warm-Start verhindert Cold-Window.** `lifespan.py` startet `asyncio.create_task(registry.awarm())` beim Startup. Blockiert den Server nicht (Provider-Fetches können lang dauern), aber nach dem ersten Request-Batch ist der Cache warm. Bis dahin: `validate_model` fail-open. `lifespan.py:124-127`
- **Custom-Modelle erscheinen NICHT im Dropdown** wenn sie nicht vom Provider live zurückkommen. `provider.models` in `llm.json` trägt Modelle nur in die Provider-Config (und damit in `use-in-agent` + Validate) ein, aber NICHT in die Registry. Das ist bewusst — Registry zeigt nur was die Provider-APIs liefern (plus Fallbacks). Folge: wer ein Custom-Modell nutzen will, muss es manuell eingeben; es erscheint nicht im Picker-Dropdown.
- **`_PURPOSE_KEYS` ist SSOT für Default-Mapping.** `_config.py::_PURPOSE_KEYS` mappt Zweck → Pfad in `llm.json`. `routes/llm.py::list_llm_models` liest damit `get_default(purpose)` und hängt es als `"default"`-Feld an die Registry-Antwort. Frontend-Pickers bekommen so Vorauswahl direkt vom Endpoint — kein zusätzlicher `GET /api/llm`. `_config.py:77`, `routes/llm.py:120-128`

- **`llm.json` ist die einzige Laufzeit-Quelle.** Provider-Keys, OAuth-Blöcke, `default_model`, `embed_model`, `media_models` leben alle hier. Mehrere Module lesen/schreiben es direkt (`routes/llm.py._load/_save`, `routes/llm_oauth.py._write_provider_oauth`, `oauth/*.resolve_*`, `_llm_config_rmw.update_provider_oauth`). Wer hier schreibt OHNE flock riskiert, einen parallelen Token-Refresh zu überschreiben.
- **OAuth-Race-Schutz nur in `_llm_config_rmw`.** `update_provider_oauth` hält `fcntl.flock` auf `llm.json.lock`, liest frisch, mutiert nur den oauth-Block, atomic-rename. Aber `routes/llm.py._save` und `routes/llm_oauth.py._write_provider_oauth` nutzen das NICHT — sie überschreiben die ganze Datei. Ein gleichzeitiger Token-Refresh (flock-geschützt) und ein UI-Save (ungeschützt) können sich gegenseitig zerstören. Praktisch selten, aber eine Falle.
- **`LlmProvider` braucht `extra="allow"`.** Ohne das würde `model_dump()` beim `PUT /api/llm` den `oauth`-Block stillschweigend droppen und alle OAuth-Logins beim ersten Save killen. Kommentar steht im Code. `routes/llm.py:23-25`
- **mtime-Cache in `_config.py`.** `load_config` cached per mtime. Ein externer Schreiber (z.B. Token-Refresh aus einem anderen Prozess) ändert mtime → Cache invalidiert. Aber: identische mtime (sub-second-Writes auf manchen FS) könnte einen Refresh maskieren. In der Praxis ok wegen `resolve_anthropic_token` direkt aus Disk liest, nicht aus dem Cache.
- **`resolve_anthropic_token`/`resolve_openai_codex_token` lesen IMMER frisch von Disk** (nicht über `load_config`-Cache), damit ein Refresh in einem anderen Prozess sofort gesehen wird.
- **Cache-Ordering bei Anthropic-Calls ist delikat** (`build_anthropic_kwargs`): OAuth-Identity zuerst, system+summary MIT `cache_control`, volatile OHNE (sonst bricht Prompt-Cache). Wer die Reihenfolge ändert, bricht Caching oder OAuth-Identity. Siehe Memory "Anthropic-Cache-Semantik".
- **MiniMax verträgt kein `cache_control` und kein system-Array.** `build_minimax_kwargs` strippt cache_control (sonst HTTP 500) und joint system zu EINEM String (Array bricht nach Compaction). `runner/_anthropic_payload.py:137-165`
- **MiniMax-Image-Workaround.** `/anthropic`-Endpoint reicht Anthropic-Image-Blocks nicht ans Modell — `convert_images_for_minimax` übersetzt zu OpenAI-`image_url`. `llm/_anthropic.py:95`
- **Effort-Capability ist SSOT-zentralisiert (#214).** `EFFORT_PARAM_MODELS` lebt nur in `_anthropic.py`; Frontend holt sie über `/llm/effort-models`. Neues 4.6+-Modell → nur diese Konstante erweitern, sonst fehlt xhigh/max im UI UND `apply_effort` nutzt den Legacy-Pfad.
- **Live-context_window hat Vorrang vor METADATA** (`_enrich`): OpenRouter/Gemini liefern aktuelle Werte; METADATA ist Fallback + Quelle für `tool_use`/`category`/`family`/`params` (die kommen NICHT live).
- **`is_free`-Semantik:** nur OpenRouter liefert pricing-Strings; bei anderen Providern bleibt `is_free=None` (Filter "nur gratis" zeigt dann nichts). `catalog.py:84-91`
- **Anthropic hat ein Live-`/v1/models`-Endpoint** (x-api-key), nutzt also NICHT die `STATIC_MODELS`-Fallback-Liste, solange ein Key/OAuth-Token vorhanden ist. `catalog.py:162` greift `api_key or oauth.access` ab.
- **Pricing-Lücken sind by-design.** OpenRouter liefert explizit `None` (Option A: Tokens zählen, Kosten NULL). Unbekannte Modelle → `cost_micros` gibt `None` → `cost_micros`-Spalte NULL, Token-Counts bleiben. Preise sind hartkodiert mit Stand 2026-05-11 — driften ohne manuelle Pflege.
- **`provider_from_model` ist eine Heuristik** (String-Prefixe), nicht die echte Provider-ID aus `llm.json`. Bei Modell-Namen ohne klares Prefix → "other" → kein Pricing. Llama/Mistral matchen auf "ollama" (historisch), was für NVIDIA-NIM-Llama falsche Provider-Zuordnung im Cost-Tracking gibt.
- **Embedding-`dim` MUSS exakt stimmen** (pgvector-Spalte). Falsche dim bricht die Suche. Deshalb sind nur explizit bekannte Embed-Modelle erlaubt (keine Live-Liste). Ein `embed_model`-Wechsel triggert Re-Embed/Backfill (`on_embed_model_change`) — ohne Re-Embed wäre die Vektor-Suche kaputt (siehe Memory "Embed-Modell OpenRouter").
- **`embed_type` (db/query) ist asymmetrie-kritisch** für NVIDIA (`input_type` passage/query) und MiniMax (`type`). Falscher Typ senkt still die Suchqualität, kein Fehler.
- **OpenRouter-Modalitäts-Filter sind unzuverlässig.** `?input_modalities=audio` liefert oft leer → `list_transcribe_models` fällt auf `_TRANSCRIBE_FALLBACK`. TTS-/Video-Modelle liegen auf EIGENEN Endpoints (`?output_modalities=speech`, `/videos/models`), NICHT im chat-`/models` — deshalb laufen sie nicht durch `candidates()`/Katalog.
- **Media-Tools sprechen OpenRouter mit NACKTEM Slug** an. `get_media_model` strippt führendes `openrouter/`. Der Katalog listet aber mit Prefix → die Übersetzung passiert genau hier.
- **`provider_env_vars()` ist die SSOT für die shell_exec-Denylist.** Neuer Provider in `_ENV_MAP` → automatisch in der Denylist geschützt. Wer Keys woanders in ENV legt, umgeht diesen Schutz.
- **OAuth-Token sind als `sk-ant-oat`-Präfix erkennbar** (`_client`, `build_anthropic_kwargs`). Ein OAuth-Token wird als `auth_token` (nicht `api_key`) + Identity-Header gesendet; ein Plain-Key als `api_key`. Verwechslung → 401 oder fehlende Claude-Code-Identität.
- **Codex-Default-Modelle sind DREIFACH dupliziert:** `_catalog_data.STATIC_MODELS["openai-codex"]`, `routes/llm_oauth.CODEX_DEFAULT_MODELS`, `frontend` (implizit). Neues Codex-Modell → an allen Stellen nachziehen, sonst Drift.
- **`MAX_TOKENS`/temperature werden bei Effort-Legacy überschrieben.** Wer auf einem Claude-4.5-Modell low/medium/high Effort setzt, bekommt zwangsweise `temperature=1.0` und `max_tokens>=budget+4096` — das überschreibt Agent-Settings still.

---

## Datenmodell

### `llm.json` (Pfad: `settings.llm_config` = `config_dir/llm.json`)
```
{
  "providers": [
    {
      "id": "anthropic|openai|openai-codex|openrouter|groq|mistral|gemini|minimax|nvidia",
      "name": "...",
      "api_key": "...",            // leer bei reinen OAuth-Providern
      "models": ["..."],            // custom/zusätzliche Modelle (UNION mit Live-Katalog)
      "group_id": "...",            // nur MiniMax (Embeddings)
      "oauth": {                    // nur OAuth-Provider (anthropic, openai-codex)
        "access": "...", "refresh": "...",
        "expires_at": <epoch_s>, "scope": "...",
        "account_id": "..."         // nur openai-codex
      }
    }
  ],
  "default_model": "...",
  "embed_model": "...",
  "media_models": { "image": "...", "music": "...", "tts": "...", "transcribe": "...", "video": "..." }
}
```

### `oauth_pending.json` (Pfad: `settings.oauth_pending_path` = `data_dir/oauth_pending.json`, chmod 0600)
`{ provider, verifier, state, ts }` — TTL 600s; nur während eines laufenden Codex-OAuth-Flows.

### `oauth_usage.json` (Pfad: `data_dir/oauth_usage.json`)
`{ updated_at, status?, representative_claim?, fallback?, reset?, 5h_utilization?, 5h_reset?, 5h_surpassed_threshold?, 7d_*?, overage_status?, overage_reset?, overage_utilization?, overage_disabled_reason?, overage_surpassed_threshold? }`

### `<llm.json>.lock` / `<llm.json>.tmp`
flock-Sidecar + Atomic-Write-Temp für `_llm_config_rmw`.

### DB: `llm_calls`-Tabelle (geschrieben in `runner/runner.py`)
Felder: `session_id, agent_id, user_id, provider, model, temperature, max_tokens, reasoning_effort, prompt_tokens, completion_tokens, cache_read_tokens, cache_creation_tokens, stop_reason, ttft_ms, total_ms, cost_micros, turn_in_session`. `cost_micros` = NULL bei unbekanntem Pricing.

### ENV-Vars
- API-Keys (gesetzt von `apply_keys` aus `llm.json`): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, `GEMINI_API_KEY`, `NVIDIA_NIM_API_KEY`. `llm/_config.py:9-17`
- Diese 7 Namen = `provider_env_vars()` (shell_exec-Denylist-SSOT).

### Konstanten / Konfig-Keys
- `_CACHE_TTL` Katalog = 300s; Speech/Transcribe/Video-TTL = 300s; MiniMax-Usage-TTL = 30s; OAuth-Refresh-Threshold = 300s; OAuth-Pending-TTL = 600s.
- `EFFORT_LEVELS`, `EFFORT_PARAM_MODELS`, `EFFORT_TO_BUDGET` — siehe WAS.
- OAuth-Konstanten: Anthropic `CLIENT_ID=9d1c250a-…`, redirect `localhost:53692`; Codex `CLIENT_ID=app_EMoamEEZ73f0CkXaXp7hrann`, redirect `localhost:1455/auth/callback`, `originator=hydrahive`.

---

## Offene Enden

- **BUG (HIGH) — `base64` nicht importiert in `oauth/openai_codex.py`.** `extract_account_id` (`:107`) ruft `base64.urlsafe_b64decode`, aber das Modul importiert nur `json`/`time`/`httpx` — KEIN `base64`. Der `NameError` wird vom `except Exception: return ""` (`:109`) verschluckt. Folge: `extract_account_id` liefert IMMER `""`; `_normalize_token_response` (`:161`) setzt `account_id=""`; der Codex-Backend-Header `chatgpt-account-id` (`_codex_provider.py:60`) ist leer. Zur Laufzeit verifiziert (siehe Bash-Test). Fix = `import base64` ergänzen. Bricht potenziell alle ChatGPT-Plus/Pro-Codex-Calls (Backend verlangt account-id).
- **Anthropic-OAuth hat keinen GUI-Flow.** `oauth/anthropic.py` exportiert `authorize_url`/`parse_callback_input`/`exchange_code`/`refresh_access_token`, aber `routes/llm_oauth.py` akzeptiert NUR `provider=="openai-codex"` in start/exchange/revoke (`:103`, `:120`, `:159`). Es gibt keinen Weg, einen Anthropic-OAuth-Block über die UI anzulegen — nur `resolve_anthropic_token` (Refresh/Resolve) ist verdrahtet. Entweder toter Code oder fehlende Verkabelung. `_llm_providers.ts` markiert `anthropic` NICHT als `auth:"oauth"`, also zeigt die UI dafür nur ein API-Key-Feld.
- **Drei Kopien der Codex-Default-Modellliste** (`_catalog_data.STATIC_MODELS`, `routes/llm_oauth.CODEX_DEFAULT_MODELS`, plus Frontend-Erwartung) — Drift-Risiko bei neuen Modellen.
- **`provider_from_model`-Heuristik mappt Llama/Mistral/Mixtral auf `"ollama"`** (`_pricing.py:78`). Für NVIDIA-NIM-Llama-Modelle ist das die falsche Provider-Zuordnung im Cost-Tracking — und `ollama` hat ohnehin keine Pricing-Tabelle → `cost_micros=None`. Für lokale Ollama-Modelle gibt es keinen Provider in `_ENV_MAP`/`PROVIDER_ENDPOINTS`, also ist `"ollama"` ein toter Pricing-Pfad.
- **Pricing-Tabellen sind statisch + datiert** (Stand 2026-05-11, Kommentar `_pricing.py:4`). `gpt-5`-Preise sind explizit als "hypothetisch" markiert (`_pricing.py:42`). Driftet ohne manuelle Pflege; keine automatische Sync mit den Live-Katalog-Preisen (OpenRouter liefert echte Preise, die aber NICHT ins Cost-Tracking fließen).
- **`oauth_usage.json`-Pfad ist hartkodiert** (`_oauth_usage.py:22`, `settings.data_dir / "oauth_usage.json"`) statt als Settings-Property wie `llm_config`/`oauth_pending_path`. Inkonsistent zur Pfad-SSOT in `settings/_paths.py`. Außerdem wird `_CACHE_FILE` zur Import-Zeit gebunden → friert `data_dir` ein (vgl. Memory "Test-Gotcha settings.data_dir Freeze").
- **`MiniMax`-Usage-Card lebt unter `features/system/`**, nicht `features/llm/` — der Endpoint ist aber `/api/llm/minimax/usage`. Co-location-Bruch (UI in anderem Feature-Folder als die zugehörige Route/API).
- **`llm/__init__.py` ist leer** — keine Package-Doku/Re-Exports; die öffentliche API liegt verstreut in `client.py` (mit Underscore-Aliasen für Backwards-Compat statt sauberem Public-Interface). Der Kommentar in `client.py:31-35` gibt zu, dass 4 Caller mit Underscore-Namen auf private Helper zugreifen.
- **`embed.py` listet `cohere` als Embed-Provider** (`:50`), aber `cohere` steht NICHT in `_ENV_MAP`/`PROVIDER_ENDPOINTS`/`KNOWN_PROVIDERS`. Cohere-Embeddings sind also nur erreichbar, wenn jemand manuell einen `cohere`-Provider in `llm.json` einträgt — der Chat-/Katalog-Pfad kennt Cohere gar nicht. Halb-verdrahtet.
- **`abab*`/`embo-01` und `MiniMax-M2.x` Versionsvielfalt** in `STATIC_MODELS`/`METADATA` wirkt teils spekulativ (z.B. `MiniMax-M2.7`, `glm5`/`glm-5.1`/`glm4.7`, `deepseek-v4-pro/flash`) — Modelle, deren Existenz/Verfügbarkeit nicht offensichtlich verifiziert ist; reine Metadata ohne Live-Gegenprüfung außer bei Providern mit `/v1/models`.
- **`test_connection` und `catalog/test` machen echte (kostende) API-Calls** — bei OpenRouter `:free`-Modellen historisch zickig (Memory "Live-Modelle SSOT"). Kein Trockenlauf-Modus.
