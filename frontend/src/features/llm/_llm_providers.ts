import type { LlmProvider } from "./api"

export const KNOWN_PROVIDERS = [
  {
    id: "anthropic", name: "Anthropic", placeholder: "sk-ant-...",
    models: ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5", "claude-sonnet-4-5", "claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022"],
  },
  {
    id: "openai", name: "OpenAI", placeholder: "sk-...",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1-preview", "o1-mini"],
  },
  {
    id: "openrouter", name: "OpenRouter", placeholder: "sk-or-...",
    models: ["anthropic/claude-sonnet-4-6", "openai/gpt-4o", "google/gemini-2.0-flash-exp", "deepseek/deepseek-r1", "meta-llama/llama-3.3-70b-instruct"],
  },
  {
    id: "groq", name: "Groq", placeholder: "gsk_...",
    models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "deepseek-r1-distill-llama-70b"],
  },
  {
    id: "mistral", name: "Mistral", placeholder: "...",
    models: ["mistral-large-latest", "mistral-small-latest", "codestral-latest", "open-mistral-nemo"],
  },
  {
    id: "gemini", name: "Google Gemini", placeholder: "AIza...",
    models: ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b"],
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
