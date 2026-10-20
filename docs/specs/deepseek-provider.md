# DeepSeek als LLM-Anbieter – Spec

Status: **FREIGEGEBEN** durch Till (20.10.2026: „könnten wir deepseek in die llm config mit aufnehmen unter admin?
also deepseek api“).

Nicht Teil davon: die zunächst geplante Sperre von LiteLLM 1.106.0. Geprüft 20.10.: Eine saubere Installation von
1.106.0 ist stimmig (`should_use_litellm_mcp_gateway` + Verweis `_should_use_litellm_mcp_gateway`). Der Fehler beim
Mac-Nutzer passt zu einem gemischten Paketstand (neue `main.py`, alte `litellm_proxy_mcp_handler.py`), nicht zu
einem Fehler der Version.

## 1. DeepSeek als Anbieter (Admin → LLM)

Quelle: offizielle Doku https://api-docs.deepseek.com/ (20.10.2026): OpenAI-kompatibel,
`base_url https://api.deepseek.com`, Bearer-Schlüssel, Modelle `deepseek-flash`, `deepseek-v4-pro`
(alte Namen werden weiter angenommen). LiteLLM kennt den Anbieter `deepseek/` (Schlüssel aus
`DEEPSEEK_API_KEY`).

| Stelle | Eintrag |
|---|---|
| `llm/_config.py` `_ENV_MAP` | `"deepseek": "DEEPSEEK_API_KEY"` (damit landet der Schlüssel automatisch in der shell_exec-Sperrliste) |
| `llm/_catalog_data.py` `PROVIDER_ENDPOINTS` | `"deepseek": {"url": "https://api.deepseek.com/models", "auth": "bearer"}` (Live-Liste, OpenAI-Format) |
| `llm/_catalog_data.py` `STATIC_MODELS` | Ersatzliste `deepseek/deepseek-flash`, `deepseek/deepseek-v4-pro` (falls die Liste nicht abrufbar ist) |
| `llm/_catalog_data.py` `PROVIDER_PREFIX` | `"deepseek": "deepseek/"` |
| `llm/model_ids.py` `_PROVIDER_PREFIXES` | `"deepseek/"` |
| `api/routes/llm_catalog.py` `_ensure_model_in_providers` | `deepseek/` → Anbieter `deepseek` |
| Frontend `features/llm/_llm_providers.ts` | `{ id: "deepseek", name: "DeepSeek", placeholder: "sk-..." }` |

Preise stehen schon in `llm/_pricing.py` (`_DEEPSEEK`, `deepseek-chat`/`deepseek-reasoner`); neue Modellnamen
bekommen dort keinen erfundenen Preis (Grundregel: Preise nie erfinden).

## 2. Tests
- DeepSeek an allen sieben Stellen; Schlüssel in `provider_env_vars()`; Katalog nimmt die Live-Liste
  (Antwort im OpenAI-Format gefälscht) und fällt ohne Netz auf die Ersatzliste zurück; Modell `deepseek/…` wird dem
  Anbieter `deepseek` zugeordnet.
