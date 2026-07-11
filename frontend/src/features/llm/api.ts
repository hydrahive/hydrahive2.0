import { api } from "@/shared/api-client"

export interface OAuthBlock {
  access?: string
  refresh?: string
  expires_at?: number
  account_id?: string
  scope?: string
}

export interface LlmProvider {
  id: string
  name: string
  api_key: string
  group_id?: string
  models: string[]
  oauth?: OAuthBlock
}

export interface LlmConfig {
  providers: LlmProvider[]
  default_model: string
  embed_model: string
  media_models?: Record<string, string>
}

export interface AnthropicRateLimits {
  updated_at?: string
  status?: string
  representative_claim?: string
  fallback?: string
  "5h_utilization"?: number
  "5h_reset"?: string
  "5h_surpassed_threshold"?: string
  "7d_utilization"?: number
  "7d_reset"?: string
  "7d_surpassed_threshold"?: string
  overage_status?: string
  overage_utilization?: number
  overage_reset?: string
}

export interface CodexUsageWindow {
  used_pct: number
  reset_in_s: number
  window_s: number
}

export interface CodexUsage {
  available: boolean
  reason?: string
  fetched_at?: string
  plan_type?: string
  primary?: CodexUsageWindow | null
  secondary?: CodexUsageWindow | null
  credits?: { has_credits?: boolean; unlimited?: boolean; balance?: number }
}

export interface OpenRouterCredits {
  available: boolean
  reason?: string
  fetched_at?: string
  total?: number
  used?: number
  remaining?: number
  used_pct?: number
}

export const llmApi = {
  getConfig: () => api.get<LlmConfig>("/llm"),
  updateConfig: (cfg: LlmConfig) => api.put<LlmConfig>("/llm", cfg),
  testConnection: (model?: string) =>
    api.post<{ ok: boolean; response: string }>("/llm/test", { model: model ?? null }),
  oauthStart: (provider: string) =>
    api.post<{ authorize_url: string; state: string }>("/llm/oauth/start", { provider }),
  oauthExchange: (provider: string, code_or_url: string) =>
    api.post<{ ok: boolean; account_id: string }>("/llm/oauth/exchange",
      { provider, code_or_url }),
  oauthRevoke: (provider: string) =>
    api.delete<{ ok: boolean }>(`/llm/oauth/${provider}`),
  getAnthropicRateLimits: () => api.get<AnthropicRateLimits>("/llm/anthropic/rate-limits"),
  getCodexUsage: () => api.get<CodexUsage>("/llm/codex/usage"),
  getOpenRouterCredits: () => api.get<OpenRouterCredits>("/llm/openrouter/credits"),
}

export interface CatalogModel {
  id: string
  context_window: number | null
  tool_use: boolean | null
  category: string
  family: string
  params?: string
  unknown: boolean
  is_free: boolean | null
  price_prompt: string | null
  price_completion: string | null
  output_modalities?: string[]
  input_modalities?: string[]
  supports_effort?: boolean
}

export interface CatalogProvider {
  provider_id: string
  provider_name: string
  configured: boolean
  models: CatalogModel[]
  live_count: number
}

export interface CatalogTestResult {
  ok: boolean
  latency_ms: number
  response?: string
  error?: string
}

export const catalogApi = {
  get: () => api.get<{ providers: CatalogProvider[] }>("/llm/catalog"),
  test: (model: string) => api.post<CatalogTestResult>("/llm/catalog/test", { model }),
  useInAgent: (agent_id: string, model: string) =>
    api.post<{ ok: boolean }>("/llm/catalog/use-in-agent", { agent_id, model }),
}

export interface RegistryModel {
  id: string
  label: string
  provider: string
  purposes: string[]
  context_window: number | null
  is_free: boolean | null
  embed_dim: number | null
}

export const llmModelsApi = {
  byModality: (modality?: string) =>
    api.get<{ models: RegistryModel[]; default: string }>(`/llm/models${modality ? `?modality=${modality}` : ""}`),
}
