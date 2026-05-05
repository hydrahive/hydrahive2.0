import { api } from "@/shared/api-client"

export interface LlmProvider {
  id: string
  name: string
  api_key: string
  models: string[]
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

export interface CatalogModel {
  id: string
  context_window: number | null
  tool_use: boolean | null
  category: string
  family: string
  params?: string
  unknown: boolean
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
