"""Static-Daten für den LLM-Catalog: Provider-Endpoints, Modell-IDs, Metadata.

Reines Datenmodul — keine Logik, kein Import von Code außerhalb.
Wird von `catalog.py` konsumiert.
"""
from __future__ import annotations

from typing import Any


# Provider-Endpoints zum Live-Modell-Listing.
# Format: provider_id → {url, auth_kind ("bearer"|"query"), query_param}
PROVIDER_ENDPOINTS = {
    "openai":     {"url": "https://api.openai.com/v1/models", "auth": "bearer"},
    "nvidia":     {"url": "https://integrate.api.nvidia.com/v1/models", "auth": "bearer"},
    "groq":       {"url": "https://api.groq.com/openai/v1/models", "auth": "bearer"},
    "mistral":    {"url": "https://api.mistral.ai/v1/models", "auth": "bearer"},
    "openrouter": {"url": "https://openrouter.ai/api/v1/models", "auth": "bearer"},
    "gemini":     {"url": "https://generativelanguage.googleapis.com/v1beta/models",
                   "auth": "query", "query_param": "key"},
    # MiniMax + OpenAI-Codex haben kein public /v1/models-Endpoint → static
    "anthropic":    {"url": "https://api.anthropic.com/v1/models", "auth": "x-api-key"},
    "minimax":      {"url": None, "auth": None},
    "openai-codex": {"url": None, "auth": None},
}

# Static-Listen für Provider ohne /v1/models-Endpoint.
STATIC_MODELS = {
    "anthropic": [
        "claude-fable-5", "claude-sonnet-5", "claude-sonnet-4-6",
        "claude-opus-4-8", "claude-opus-4-7",
        "claude-haiku-4-5", "claude-sonnet-4-5", "claude-3-7-sonnet-20250219",
        "claude-3-5-haiku-20241022",
    ],
    "minimax": [
        "MiniMax-Text-01", "MiniMax-M2", "MiniMax-M2.1", "MiniMax-M2.7", "MiniMax-M1",
        "abab6.5s-chat", "abab6.5-chat", "abab5.5-chat", "abab5.5s-chat",
        "embo-01",
    ],
    "openai-codex": [
        "openai-codex/gpt-5.6-sol",
        "openai-codex/gpt-5.6-terra",
        "openai-codex/gpt-5.6-luna",
        "openai-codex/gpt-5.5",
        "openai-codex/gpt-5.4",
        "openai-codex/gpt-5.1",
        "openai-codex/gpt-5.1-codex-max",
        "openai-codex/gpt-5.1-codex-mini",
    ],
}

# Modell-Prefix für LiteLLM bei Provider die das brauchen.
PROVIDER_PREFIX = {
    "openai": "openai/", "nvidia": "nvidia_nim/", "groq": "groq/",
    "mistral": "mistral/", "openrouter": "openrouter/", "gemini": "gemini/",
}

# Interne Metadata-Tabelle. Per Modell-ID (mit Prefix) → Eigenschaften.
# tool_use: True/False/None (None = ungetestet/unbekannt).
METADATA: dict[str, dict[str, Any]] = {
    # Anthropic
    "claude-fable-5":    {"context_window": 1_000_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-sonnet-5":   {"context_window": 1_000_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-opus-4-8":   {"context_window": 1_000_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-opus-4-7":   {"context_window": 1_000_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-sonnet-4-6": {"context_window": 1_000_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-sonnet-4-5": {"context_window": 200_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-haiku-4-5":  {"context_window": 200_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-3-7-sonnet-20250219": {"context_window": 200_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    "claude-3-5-haiku-20241022":  {"context_window": 200_000, "tool_use": True, "category": "chat", "family": "anthropic"},
    # MiniMax
    "MiniMax-Text-01": {"context_window": 1_000_000, "tool_use": True, "category": "chat", "family": "minimax"},
    "MiniMax-M1":      {"context_window": 1_000_000, "tool_use": True, "category": "chat", "family": "minimax"},
    "MiniMax-M2":      {"context_window": 256_000, "tool_use": True, "category": "chat", "family": "minimax"},
    "MiniMax-M2.1":    {"context_window": 205_000, "tool_use": True, "category": "chat", "family": "minimax"},
    "MiniMax-M2.7":    {"context_window": 256_000, "tool_use": True, "category": "chat", "family": "minimax"},
    "abab6.5s-chat":   {"context_window": 245_000, "tool_use": True, "category": "chat", "family": "minimax"},
    "abab6.5-chat":    {"context_window": 8_192, "tool_use": True, "category": "chat", "family": "minimax"},
    "abab5.5-chat":    {"context_window": 16_384, "tool_use": False, "category": "chat", "family": "minimax"},
    "abab5.5s-chat":   {"context_window": 8_192, "tool_use": False, "category": "chat", "family": "minimax"},
    "embo-01":         {"context_window": 4_096, "tool_use": False, "category": "embed", "family": "minimax"},
    # NVIDIA NIM — empirisch verifiziert wo möglich
    # Meta Llama
    "nvidia_nim/meta/llama-3.3-70b-instruct":           {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "llama",    "params": "70B"},
    "nvidia_nim/meta/llama-3.1-405b-instruct":          {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "llama",    "params": "405B"},
    "nvidia_nim/meta/llama-3.1-70b-instruct":           {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "llama",    "params": "70B"},
    "nvidia_nim/meta/llama-3.1-8b-instruct":            {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "llama",    "params": "8B"},
    "nvidia_nim/meta/llama-3.2-90b-vision-instruct":    {"context_window": 128_000, "tool_use": True,  "category": "vision",      "family": "llama",    "params": "90B"},
    "nvidia_nim/meta/llama-3.2-11b-vision-instruct":    {"context_window": 128_000, "tool_use": True,  "category": "vision",      "family": "llama",    "params": "11B"},
    "nvidia_nim/meta/llama-3.2-3b-instruct":            {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "llama",    "params": "3B"},
    "nvidia_nim/meta/llama-3.2-1b-instruct":            {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "llama",    "params": "1B"},
    "nvidia_nim/meta/llama-4-maverick-17b-128e-instruct": {"context_window": 128_000, "tool_use": True, "category": "chat",       "family": "llama",    "params": "17B-MoE"},
    "nvidia_nim/meta/llama-guard-4-12b":                {"context_window": 8_192,   "tool_use": False, "category": "safety",      "family": "llama",    "params": "12B"},
    "nvidia_nim/meta/llama2-70b":                       {"context_window": 4_096,   "tool_use": False, "category": "chat",        "family": "llama",    "params": "70B"},
    "nvidia_nim/meta/codellama-70b":                    {"context_window": 16_384,  "tool_use": False, "category": "code",        "family": "llama",    "params": "70B"},
    # Qwen
    "nvidia_nim/qwen/qwen2.5-coder-32b-instruct":       {"context_window": 32_768,  "tool_use": True,  "category": "code",        "family": "qwen",     "params": "32B"},
    "nvidia_nim/qwen/qwen3-next-80b-a3b-instruct":      {"context_window": 262_144, "tool_use": True,  "category": "chat",        "family": "qwen",     "params": "80B-MoE"},
    "nvidia_nim/qwen/qwen3-next-80b-a3b-thinking":      {"context_window": 262_144, "tool_use": True,  "category": "reasoning",   "family": "qwen",     "params": "80B-MoE"},
    "nvidia_nim/qwen/qwen3-coder-480b-a35b-instruct":   {"context_window": 262_144, "tool_use": True,  "category": "code",        "family": "qwen",     "params": "480B-MoE"},
    "nvidia_nim/qwen/qwen3.5-122b-a10b":                {"context_window": 262_144, "tool_use": True,  "category": "chat",        "family": "qwen",     "params": "122B-MoE"},
    "nvidia_nim/qwen/qwen3.5-397b-a17b":                {"context_window": 262_144, "tool_use": True,  "category": "chat",        "family": "qwen",     "params": "397B-MoE"},
    # Mistral
    "nvidia_nim/mistralai/mistral-large-3-675b-instruct-2512": {"context_window": 128_000, "tool_use": True, "category": "chat",  "family": "mistral",  "params": "675B"},
    "nvidia_nim/mistralai/mistral-large-2-instruct":    {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "mistral",  "params": "123B"},
    "nvidia_nim/mistralai/mistral-large":               {"context_window": 32_768,  "tool_use": True,  "category": "chat",        "family": "mistral",  "params": "123B"},
    "nvidia_nim/mistralai/mistral-medium-3-instruct":   {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "mistral",  "params": "123B"},
    "nvidia_nim/mistralai/mistral-medium-3.5-128b":     {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "mistral",  "params": "128B"},
    "nvidia_nim/mistralai/mistral-small-4-119b-2603":   {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "mistral",  "params": "119B"},
    "nvidia_nim/mistralai/mistral-7b-instruct-v0.3":    {"context_window": 32_768,  "tool_use": True,  "category": "chat",        "family": "mistral",  "params": "7B"},
    "nvidia_nim/mistralai/mistral-nemotron":            {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "mistral",  "params": "123B"},
    "nvidia_nim/mistralai/mixtral-8x7b-instruct-v0.1":  {"context_window": 32_768,  "tool_use": True,  "category": "chat",        "family": "mistral",  "params": "8x7B-MoE"},
    "nvidia_nim/mistralai/mixtral-8x22b-instruct-v0.1": {"context_window": 65_536,  "tool_use": True,  "category": "chat",        "family": "mistral",  "params": "8x22B-MoE"},
    "nvidia_nim/mistralai/mixtral-8x22b-v0.1":          {"context_window": 65_536,  "tool_use": False, "category": "chat",        "family": "mistral",  "params": "8x22B-MoE"},
    "nvidia_nim/mistralai/codestral-22b-instruct-v0.1": {"context_window": 32_768,  "tool_use": False, "category": "code",        "family": "mistral",  "params": "22B"},
    "nvidia_nim/mistralai/devstral-2-123b-instruct-2512": {"context_window": 128_000, "tool_use": True, "category": "code",       "family": "mistral",  "params": "123B"},
    "nvidia_nim/mistralai/ministral-14b-instruct-2512": {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "mistral",  "params": "14B"},
    "nvidia_nim/mistralai/magistral-small-2506":        {"context_window": 40_000,  "tool_use": False, "category": "reasoning",   "family": "mistral",  "params": "24B"},
    "nvidia_nim/nv-mistralai/mistral-nemo-12b-instruct": {"context_window": 128_000, "tool_use": True, "category": "chat",        "family": "mistral",  "params": "12B"},
    # Google Gemma
    "nvidia_nim/google/gemma-4-31b-it":                 {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "gemma",    "params": "31B"},
    "nvidia_nim/google/gemma-3-27b-it":                 {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "gemma",    "params": "27B"},
    "nvidia_nim/google/gemma-3-12b-it":                 {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "gemma",    "params": "12B"},
    "nvidia_nim/google/gemma-3-4b-it":                  {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "gemma",    "params": "4B"},
    "nvidia_nim/google/gemma-3n-e4b-it":                {"context_window": 32_768,  "tool_use": False, "category": "chat",        "family": "gemma",    "params": "4B"},
    "nvidia_nim/google/gemma-3n-e2b-it":                {"context_window": 32_768,  "tool_use": False, "category": "chat",        "family": "gemma",    "params": "2B"},
    "nvidia_nim/google/gemma-2-2b-it":                  {"context_window": 8_192,   "tool_use": False, "category": "chat",        "family": "gemma",    "params": "2B"},
    "nvidia_nim/google/gemma-2b":                       {"context_window": 8_192,   "tool_use": False, "category": "chat",        "family": "gemma",    "params": "2B"},
    "nvidia_nim/google/recurrentgemma-2b":              {"context_window": 4_096,   "tool_use": False, "category": "chat",        "family": "gemma",    "params": "2B"},
    "nvidia_nim/google/codegemma-1.1-7b":               {"context_window": 8_192,   "tool_use": False, "category": "code",        "family": "gemma",    "params": "7B"},
    "nvidia_nim/google/codegemma-7b":                   {"context_window": 8_192,   "tool_use": False, "category": "code",        "family": "gemma",    "params": "7B"},
    "nvidia_nim/google/deplot":                         {"context_window": 4_096,   "tool_use": False, "category": "vision",      "family": "google"},
    # Microsoft Phi
    "nvidia_nim/microsoft/phi-4-multimodal-instruct":   {"context_window": 128_000, "tool_use": True,  "category": "vision",      "family": "phi",      "params": "5.6B"},
    "nvidia_nim/microsoft/phi-4-mini-instruct":         {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "phi",      "params": "3.8B"},
    "nvidia_nim/microsoft/phi-3.5-moe-instruct":        {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "phi",      "params": "16x3.8B-MoE"},
    "nvidia_nim/microsoft/phi-3-vision-128k-instruct":  {"context_window": 128_000, "tool_use": False, "category": "vision",      "family": "phi",      "params": "4.2B"},
    "nvidia_nim/microsoft/kosmos-2":                    {"context_window": 2_048,   "tool_use": False, "category": "vision",      "family": "microsoft"},
    # IBM Granite
    "nvidia_nim/ibm/granite-3.0-8b-instruct":           {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "granite",  "params": "8B"},
    "nvidia_nim/ibm/granite-3.0-3b-a800m-instruct":     {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "granite",  "params": "3B-MoE"},
    "nvidia_nim/ibm/granite-34b-code-instruct":         {"context_window": 8_192,   "tool_use": False, "category": "code",        "family": "granite",  "params": "34B"},
    "nvidia_nim/ibm/granite-8b-code-instruct":          {"context_window": 4_096,   "tool_use": False, "category": "code",        "family": "granite",  "params": "8B"},
    # DeepSeek
    "nvidia_nim/deepseek-ai/deepseek-v4-pro":           {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "deepseek"},
    "nvidia_nim/deepseek-ai/deepseek-v4-flash":         {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "deepseek"},
    "nvidia_nim/deepseek-ai/deepseek-coder-6.7b-instruct": {"context_window": 16_384, "tool_use": False, "category": "code",      "family": "deepseek", "params": "6.7B"},
    # Kimi / MoonShot
    "nvidia_nim/moonshotai/kimi-k2-instruct":           {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "kimi"},
    "nvidia_nim/moonshotai/kimi-k2-instruct-0905":      {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "kimi"},
    "nvidia_nim/moonshotai/kimi-k2-thinking":           {"context_window": 128_000, "tool_use": True,  "category": "reasoning",   "family": "kimi"},
    "nvidia_nim/moonshotai/kimi-k2.6":                  {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "kimi"},
    # OpenAI OSS
    "nvidia_nim/openai/gpt-oss-120b":                   {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "gpt-oss",  "params": "120B"},
    "nvidia_nim/openai/gpt-oss-20b":                    {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "gpt-oss",  "params": "20B"},
    # MiniMax via NVIDIA
    "nvidia_nim/minimaxai/minimax-m2.5":                {"context_window": 256_000, "tool_use": True,  "category": "chat",        "family": "minimax"},
    "nvidia_nim/minimaxai/minimax-m2.7":                {"context_window": 256_000, "tool_use": True,  "category": "chat",        "family": "minimax"},
    # NVIDIA eigene Modelle
    "nvidia_nim/nvidia/llama-3.1-nemotron-ultra-253b-v1":    {"context_window": 128_000, "tool_use": True,  "category": "chat",   "family": "nemotron", "params": "253B"},
    "nvidia_nim/nvidia/llama-3.1-nemotron-70b-instruct":     {"context_window": 128_000, "tool_use": True,  "category": "chat",   "family": "nemotron", "params": "70B"},
    "nvidia_nim/nvidia/llama-3.1-nemotron-51b-instruct":     {"context_window": 128_000, "tool_use": True,  "category": "chat",   "family": "nemotron", "params": "51B"},
    "nvidia_nim/nvidia/llama-3.1-nemotron-nano-8b-v1":       {"context_window": 128_000, "tool_use": True,  "category": "chat",   "family": "nemotron", "params": "8B"},
    "nvidia_nim/nvidia/llama-3.1-nemotron-nano-vl-8b-v1":    {"context_window": 128_000, "tool_use": False, "category": "vision",  "family": "nemotron", "params": "8B"},
    "nvidia_nim/nvidia/llama-3.3-nemotron-super-49b-v1":     {"context_window": 128_000, "tool_use": True,  "category": "chat",   "family": "nemotron", "params": "49B"},
    "nvidia_nim/nvidia/llama-3.3-nemotron-super-49b-v1.5":   {"context_window": 128_000, "tool_use": True,  "category": "chat",   "family": "nemotron", "params": "49B"},
    "nvidia_nim/nvidia/nvidia-nemotron-nano-9b-v2":          {"context_window": 128_000, "tool_use": True,  "category": "chat",   "family": "nemotron", "params": "9B"},
    "nvidia_nim/nvidia/nemotron-4-340b-instruct":            {"context_window": 4_096,   "tool_use": True,  "category": "chat",   "family": "nemotron", "params": "340B"},
    "nvidia_nim/nvidia/nemotron-4-340b-reward":              {"context_window": 4_096,   "tool_use": False, "category": "specialized", "family": "nemotron", "params": "340B"},
    "nvidia_nim/nvidia/nemotron-3-super-120b-a12b":          {"context_window": 128_000, "tool_use": True,  "category": "chat",   "family": "nemotron", "params": "120B-MoE"},
    "nvidia_nim/nvidia/nemotron-3-nano-30b-a3b":             {"context_window": 32_768,  "tool_use": False, "category": "chat",   "family": "nemotron", "params": "30B-MoE"},
    "nvidia_nim/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning": {"context_window": 32_768, "tool_use": False, "category": "reasoning", "family": "nemotron", "params": "30B-MoE"},
    "nvidia_nim/nvidia/nemotron-nano-3-30b-a3b":             {"context_window": 128_000, "tool_use": True,  "category": "chat",   "family": "nemotron", "params": "30B-MoE"},
    "nvidia_nim/nvidia/nemotron-nano-12b-v2-vl":             {"context_window": 128_000, "tool_use": False, "category": "vision",  "family": "nemotron", "params": "12B"},
    "nvidia_nim/nvidia/nemotron-mini-4b-instruct":           {"context_window": 4_096,   "tool_use": False, "category": "chat",   "family": "nemotron", "params": "4B"},
    "nvidia_nim/nvidia/nemotron-content-safety-reasoning-4b": {"context_window": 8_192,  "tool_use": False, "category": "safety",  "family": "nemotron", "params": "4B"},
    "nvidia_nim/nvidia/nemotron-3-content-safety":           {"context_window": 4_096,   "tool_use": False, "category": "safety",  "family": "nemotron"},
    "nvidia_nim/nvidia/llama-3.1-nemoguard-8b-content-safety": {"context_window": 8_192, "tool_use": False, "category": "safety",  "family": "nemotron", "params": "8B"},
    "nvidia_nim/nvidia/llama-3.1-nemoguard-8b-topic-control":  {"context_window": 8_192, "tool_use": False, "category": "safety",  "family": "nemotron", "params": "8B"},
    "nvidia_nim/nvidia/llama-3.1-nemotron-safety-guard-8b-v3": {"context_window": 8_192, "tool_use": False, "category": "safety",  "family": "nemotron", "params": "8B"},
    "nvidia_nim/nvidia/llama3-chatqa-1.5-70b":               {"context_window": 128_000, "tool_use": False, "category": "chat",   "family": "nvidia",   "params": "70B"},
    "nvidia_nim/nvidia/mistral-nemo-minitron-8b-8k-instruct": {"context_window": 8_192,  "tool_use": False, "category": "chat",   "family": "nvidia",   "params": "8B"},
    "nvidia_nim/nvidia/cosmos-reason2-8b":                   {"context_window": 32_768,  "tool_use": False, "category": "reasoning", "family": "nvidia", "params": "8B"},
    "nvidia_nim/nvidia/ising-calibration-1-35b-a3b":         {"context_window": 32_768,  "tool_use": False, "category": "specialized", "family": "nvidia", "params": "35B-MoE"},
    "nvidia_nim/nvidia/neva-22b":                            {"context_window": 4_096,   "tool_use": False, "category": "vision",  "family": "nvidia",   "params": "22B"},
    "nvidia_nim/nvidia/vila":                                {"context_window": 4_096,   "tool_use": False, "category": "vision",  "family": "nvidia"},
    "nvidia_nim/nvidia/riva-translate-4b-instruct":          {"context_window": 4_096,   "tool_use": False, "category": "translation", "family": "nvidia", "params": "4B"},
    "nvidia_nim/nvidia/riva-translate-4b-instruct-v1.1":     {"context_window": 4_096,   "tool_use": False, "category": "translation", "family": "nvidia", "params": "4B"},
    "nvidia_nim/nvidia/nv-embed-v1":                         {"context_window": 32_768,  "tool_use": False, "category": "embed",   "family": "nvidia"},
    "nvidia_nim/nvidia/nv-embedqa-e5-v5":                    {"context_window": 512,     "tool_use": False, "category": "embed",   "family": "nvidia"},
    "nvidia_nim/nvidia/nvclip":                              {"context_window": 77,      "tool_use": False, "category": "embed",   "family": "nvidia"},
    "nvidia_nim/nvidia/nemoretriever-parse":                 {"context_window": 8_192,   "tool_use": False, "category": "specialized", "family": "nvidia"},
    "nvidia_nim/nvidia/nemotron-parse":                      {"context_window": 8_192,   "tool_use": False, "category": "specialized", "family": "nvidia"},
    "nvidia_nim/nvidia/gliner-pii":                          {"context_window": 512,     "tool_use": False, "category": "specialized", "family": "nvidia"},
    "nvidia_nim/nvidia/ai-synthetic-video-detector":         {"context_window": None,    "tool_use": False, "category": "specialized", "family": "nvidia"},
    # BigCode
    "nvidia_nim/bigcode/starcoder2-15b":                {"context_window": 16_384,  "tool_use": False, "category": "code",        "family": "starcoder", "params": "15B"},
    # Databricks
    "nvidia_nim/databricks/dbrx-instruct":              {"context_window": 32_768,  "tool_use": True,  "category": "chat",        "family": "dbrx",     "params": "132B-MoE"},
    # ByteDance
    "nvidia_nim/bytedance/seed-oss-36b-instruct":       {"context_window": 65_536,  "tool_use": True,  "category": "chat",        "family": "seed",     "params": "36B"},
    # 01.AI
    "nvidia_nim/01-ai/yi-large":                        {"context_window": 32_768,  "tool_use": False, "category": "chat",        "family": "yi",       "params": "34B"},
    # AbacusAI
    "nvidia_nim/abacusai/dracarys-llama-3.1-70b-instruct": {"context_window": 128_000, "tool_use": True, "category": "chat",      "family": "llama",    "params": "70B"},
    # Adept
    "nvidia_nim/adept/fuyu-8b":                         {"context_window": 16_384,  "tool_use": False, "category": "vision",      "family": "adept",    "params": "8B"},
    # AI21 Labs
    "nvidia_nim/ai21labs/jamba-1.5-large-instruct":     {"context_window": 256_000, "tool_use": True,  "category": "chat",        "family": "jamba",    "params": "94B"},
    # AI Singapore
    "nvidia_nim/aisingapore/sea-lion-7b-instruct":      {"context_window": 4_096,   "tool_use": False, "category": "chat",        "family": "sea-lion", "params": "7B"},
    # BAAI
    "nvidia_nim/baai/bge-m3":                           {"context_window": 8_192,   "tool_use": False, "category": "embed",       "family": "bge"},
    # Writer
    "nvidia_nim/writer/palmyra-creative-122b":          {"context_window": 32_768,  "tool_use": False, "category": "chat",        "family": "palmyra",  "params": "122B"},
    "nvidia_nim/writer/palmyra-fin-70b-32k":            {"context_window": 32_768,  "tool_use": False, "category": "chat",        "family": "palmyra",  "params": "70B"},
    "nvidia_nim/writer/palmyra-med-70b":                {"context_window": 8_192,   "tool_use": False, "category": "chat",        "family": "palmyra",  "params": "70B"},
    "nvidia_nim/writer/palmyra-med-70b-32k":            {"context_window": 32_768,  "tool_use": False, "category": "chat",        "family": "palmyra",  "params": "70B"},
    # Upstage
    "nvidia_nim/upstage/solar-10.7b-instruct":          {"context_window": 4_096,   "tool_use": True,  "category": "chat",        "family": "solar",    "params": "10.7B"},
    # StepFun
    "nvidia_nim/stepfun-ai/step-3.5-flash":             {"context_window": 32_768,  "tool_use": True,  "category": "chat",        "family": "stepfun"},
    # Stockmark (Japanese)
    "nvidia_nim/stockmark/stockmark-2-100b-instruct":   {"context_window": 128_000, "tool_use": False, "category": "chat",        "family": "stockmark", "params": "100B"},
    # Sarvam (Indian languages)
    "nvidia_nim/sarvamai/sarvam-m":                     {"context_window": 32_768,  "tool_use": False, "category": "chat",        "family": "sarvam"},
    # Zyphra
    "nvidia_nim/zyphra/zamba2-7b-instruct":             {"context_window": 4_096,   "tool_use": False, "category": "chat",        "family": "zamba",    "params": "7B"},
    # Zhipu AI GLM
    "nvidia_nim/z-ai/glm5":                             {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "glm"},
    "nvidia_nim/z-ai/glm-5.1":                         {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "glm"},
    "nvidia_nim/z-ai/glm4.7":                           {"context_window": 128_000, "tool_use": True,  "category": "chat",        "family": "glm"},
    # OpenAI
    "openai/gpt-5":      {"context_window": 400_000, "tool_use": True, "category": "chat", "family": "gpt"},
    "openai/gpt-5-mini": {"context_window": 400_000, "tool_use": True, "category": "chat", "family": "gpt"},
    "openai/gpt-4o":     {"context_window": 128_000, "tool_use": True, "category": "chat", "family": "gpt"},
    "openai/gpt-4o-mini":{"context_window": 128_000, "tool_use": True, "category": "chat", "family": "gpt"},
    "openai/o1-preview": {"context_window": 128_000, "tool_use": False, "category": "reasoning", "family": "gpt"},
    "openai/o1-mini":    {"context_window": 128_000, "tool_use": False, "category": "reasoning", "family": "gpt"},
    # OpenAI Codex (ChatGPT Plus/Pro via OAuth — Responses-API).
    # Context-Windows: gpt-5-Klasse hat ~272k bei OpenAI dokumentiert; codex-Varianten
    # geben ~400k im Codex-Backend frei. Tool-Use bei allen Codex-Modellen.
    "openai-codex/gpt-5.6-sol":          {"context_window": 1_000_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.6-terra":        {"context_window": 1_000_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.6-luna":         {"context_window": 1_000_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.5":              {"context_window": 400_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.4":              {"context_window": 400_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.3-codex":        {"context_window": 400_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.3-codex-spark":  {"context_window": 400_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.2":              {"context_window": 400_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.2-codex":        {"context_window": 400_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.1":              {"context_window": 272_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.1-codex-max":    {"context_window": 400_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
    "openai-codex/gpt-5.1-codex-mini":   {"context_window": 200_000, "tool_use": True, "category": "code", "family": "gpt-codex"},
}
