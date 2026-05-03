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
