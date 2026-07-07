import type { LlmProvider } from "./api"

export const KNOWN_PROVIDERS = [
  {
    // Hybrid: API-Key-Feld bleibt (Weg 1 sk-ant-api03, Weg 2 sk-ant-oat01 via
    // `claude setup-token`) UND zusätzlich optionaler OAuth-Login (Weg 3).
    // oauthOptional versteckt das Key-Feld NICHT (anders als auth:"oauth").
    id: "anthropic", name: "Anthropic", placeholder: "sk-ant-...",
    oauthOptional: true as const,
    models: [],
  },
  {
    // LiteLLM-Routing: alle non-Anthropic/non-MiniMax Modelle MÜSSEN den Provider-Prefix haben.
    id: "openai", name: "OpenAI", placeholder: "sk-...",
    models: [],
  },
  {
    // OAuth-Provider: ChatGPT Plus/Pro via Codex-Backend (chatgpt.com).
    // Kein API-Key — Login per OAuth, Token landet als oauth-Block in llm.json.
    id: "openai-codex", name: "ChatGPT Plus/Pro (Codex)", placeholder: "OAuth — kein Key nötig",
    auth: "oauth" as const,
    models: [],
  },
  {
    id: "openrouter", name: "OpenRouter", placeholder: "sk-or-...",
    models: [],
  },
  {
    id: "groq", name: "Groq", placeholder: "gsk_...",
    models: [],
  },
  {
    id: "mistral", name: "Mistral", placeholder: "...",
    models: [],
  },
  {
    id: "gemini", name: "Google Gemini", placeholder: "AIza...",
    models: [],
  },
  {
    id: "minimax", name: "MiniMax", placeholder: "eyJ...",
    models: [],
  },
  {
    id: "nvidia", name: "NVIDIA NIM", placeholder: "nvapi-...",
    models: [],
  },
]

export const EMPTY_PROVIDER: LlmProvider = { id: "", name: "", api_key: "", models: [] }
