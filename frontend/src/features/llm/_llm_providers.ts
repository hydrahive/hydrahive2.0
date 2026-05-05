import type { LlmProvider } from "./api"

export const KNOWN_PROVIDERS = [
  {
    id: "anthropic", name: "Anthropic", placeholder: "sk-ant-...",
    models: ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5", "claude-sonnet-4-5", "claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022"],
  },
  {
    // LiteLLM-Routing: alle non-Anthropic/non-MiniMax Modelle MÜSSEN den Provider-Prefix haben.
    id: "openai", name: "OpenAI", placeholder: "sk-...",
    models: ["openai/gpt-4o", "openai/gpt-4o-mini", "openai/gpt-4-turbo", "openai/gpt-4", "openai/gpt-3.5-turbo", "openai/o1-preview", "openai/o1-mini"],
  },
  {
    id: "openrouter", name: "OpenRouter", placeholder: "sk-or-...",
    models: ["openrouter/anthropic/claude-sonnet-4-6", "openrouter/openai/gpt-4o", "openrouter/google/gemini-2.0-flash-exp", "openrouter/deepseek/deepseek-r1", "openrouter/meta-llama/llama-3.3-70b-instruct"],
  },
  {
    id: "groq", name: "Groq", placeholder: "gsk_...",
    models: ["groq/llama-3.3-70b-versatile", "groq/llama-3.1-8b-instant", "groq/mixtral-8x7b-32768", "groq/deepseek-r1-distill-llama-70b"],
  },
  {
    id: "mistral", name: "Mistral", placeholder: "...",
    models: ["mistral/mistral-large-latest", "mistral/mistral-small-latest", "mistral/codestral-latest", "mistral/open-mistral-nemo"],
  },
  {
    id: "gemini", name: "Google Gemini", placeholder: "AIza...",
    models: ["gemini/gemini-2.0-flash-exp", "gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash", "gemini/gemini-1.5-flash-8b"],
  },
  {
    id: "minimax", name: "MiniMax", placeholder: "eyJ...",
    models: ["MiniMax-M2", "MiniMax-M2.7", "abab6.5s-chat"],
  },
  {
    id: "nvidia", name: "NVIDIA NIM", placeholder: "nvapi-...",
    models: [
      "nvidia_nim/qwen/qwen2.5-coder-32b-instruct",
      "nvidia_nim/mistralai/codestral-22b-v0.1",
      "nvidia_nim/bigcode/starcoder2-15b",
      "nvidia_nim/qwen/qwq-32b-preview",
      "nvidia_nim/deepseek-ai/deepseek-r1",
      "nvidia_nim/meta/llama-3.3-70b-instruct",
      "nvidia_nim/meta/llama-3.1-405b-instruct",
      "nvidia_nim/nvidia/llama-3.1-nemotron-70b-instruct",
      "nvidia_nim/mistralai/mistral-large-2-instruct",
    ],
  },
]

export const EMPTY_PROVIDER: LlmProvider = { id: "", name: "", api_key: "", models: [] }
