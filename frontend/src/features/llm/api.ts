import { api } from "@/shared/api-client"

export interface OAuthBlock {
  access: string
  refresh: string
  expires_at: number
  scope: string
}

export interface LlmProvider {
  id: string
  name: string
  api_key: string
  models: string[]
  oauth?: OAuthBlock | null
}

export interface LlmConfig {
  providers: LlmProvider[]
  default_model: string
  embed_model: string
}

export interface EmbedModel {
  model: string
  dim: number
  provider: string
}

export const llmApi = {
  getConfig: () => api.get<LlmConfig>("/llm"),
  updateConfig: (cfg: LlmConfig) => api.put<LlmConfig>("/llm", cfg),
  testConnection: (model?: string) =>
    api.post<{ ok: boolean; response: string }>("/llm/test", { model: model ?? null }),
  getEmbedModels: () => api.get<EmbedModel[]>("/llm/embed-models"),
}

export const oauthApi = {
  startAnthropic: () =>
    api.post<{ authorize_url: string; state: string }>("/oauth/anthropic/start", {}),
  exchangeAnthropic: (code_or_url: string, state: string) =>
    api.post<{ ok: boolean; expires_at: number }>("/oauth/anthropic/exchange", { code_or_url, state }),
  refreshAnthropic: () =>
    api.post<{ ok: boolean; expires_at: number }>("/oauth/anthropic/refresh", {}),
}
