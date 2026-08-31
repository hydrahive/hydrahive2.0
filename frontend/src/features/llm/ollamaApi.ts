import { api } from "@/shared/api-client"

export type OllamaFitLevel = "perfect" | "good" | "marginal" | "too_tight" | "unknown"

export interface OllamaModel {
  id: string
  ollama_name: string
  installed: boolean
  family: string
  size: number | null
  digest?: string
  modified_at?: string | null
  parameter_size?: string | null
  quantization?: string | null
  context_window?: number | null
  capabilities: string[]
  input_modalities: string[]
  output_modalities: string[]
  fit: OllamaFitLevel
  score?: number | null
  memory_required_gb?: number | null
  memory_available_gb?: number | null
  estimated_tps?: number | null
  measured_tps?: number | null
  estimate_confidence?: string | null
  run_mode?: string | null
  best_quant?: string | null
}

export interface OllamaFamily {
  name: string
  description?: string
  capabilities: string[]
  parameter_sizes?: string[]
  installed_count?: number
  installed_models?: string[]
}

export interface OllamaPullJob {
  id: string
  model: string
  status: "queued" | "pulling" | "success" | "failed"
  phase: string
  total: number | null
  completed: number | null
  error: string | null
}

export interface OllamaCatalog {
  configured: boolean
  connected: boolean
  connection_error: string | null
  library_error: string | null
  hardware_fit: {
    available: boolean
    reason?: string | null
    system?: Record<string, unknown> | null
  }
  families: OllamaFamily[]
  installed_models: OllamaModel[]
}

export const ollamaCatalogApi = {
  get: () => api.get<OllamaCatalog>("/llm/catalog/ollama"),
  family: (family: string) => api.get<{ family: OllamaFamily; models: OllamaModel[] }>(
    `/llm/catalog/ollama/library/${encodeURIComponent(family)}`,
  ),
  pull: (model: string) => api.post<OllamaPullJob>("/llm/catalog/ollama/pulls", { model }),
  pullStatus: (jobId: string) => api.get<OllamaPullJob>(`/llm/catalog/ollama/pulls/${encodeURIComponent(jobId)}`),
  delete: (model: string) => api.delete<{ ok: boolean; model: string }>(
    `/llm/catalog/ollama/models/${encodeURIComponent(model)}`,
  ),
}
