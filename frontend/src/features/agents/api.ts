import { api } from "@/shared/api-client"
import type { Agent, AgentCreate, AgentDefaults, AgentTemplate, ToolMeta } from "./types"
import type { CatalogModel } from "@/features/llm/api"

export const agentsApi = {
  list: () => api.get<Agent[]>("/agents"),
  get: (id: string) => api.get<Agent>(`/agents/${id}`),
  create: (req: AgentCreate) => api.post<Agent>("/agents", req),
  update: (id: string, fields: Partial<AgentCreate & { status: string }>) =>
    api.patch<Agent>(`/agents/${id}`, fields),
  delete: (id: string) => api.delete<void>(`/agents/${id}`),
  getSystemPrompt: (id: string) =>
    api.get<{ prompt: string }>(`/agents/${id}/system_prompt`),
  setSystemPrompt: (id: string, prompt: string) =>
    api.put<{ prompt: string }>(`/agents/${id}/system_prompt`, { prompt }),
  getSoul: (id: string) =>
    api.get<{ components: Record<string, string> }>(`/agents/${id}/soul`),
  setSoulComponent: (id: string, component: string, content: string) =>
    api.put<{ component: string; saved: boolean }>(`/agents/${id}/soul/${component}`, { content }),
  getSoulTemplates: (id: string) =>
    api.get<{ templates: Record<string, string>; agent_type: string }>(`/agents/${id}/soul/templates`),
  applySoulTemplate: (id: string) =>
    api.post<{ applied: string[] }>(`/agents/${id}/soul/apply-template`, {}),
  listTools: () => api.get<ToolMeta[]>("/agents/_meta/tools"),
  getDefaults: () => api.get<AgentDefaults>("/agents/_meta/defaults"),
  listTemplates: () => api.get<AgentTemplate[]>("/agents/_meta/templates"),
}

export interface LlmProviderInfo {
  models: string[]              // IDs (Abwärtskompat. für CompactionSection/Fallback)
  catalog: CatalogModel[]       // strukturiert (für ModelTab-Combobox: free-Badge/Filter)
  default_model: string
}

export const llmInfoApi = {
  getModels: async (): Promise<LlmProviderInfo> => {
    const [cfg, cat] = await Promise.all([
      api.get<{ default_model: string; providers: { models: string[] }[] }>("/llm"),
      api.get<{ providers: { models: CatalogModel[] }[] }>("/llm/catalog"),
    ])
    const live = cat.providers.flatMap((p) => p.models)
    const liveIds = new Set(live.map((m) => m.id))
    // custom-Modelle (manuell in provider.models eingetragen), die NICHT live sind:
    const customIds = cfg.providers.flatMap((p) => p.models).filter((id) => id && !liveIds.has(id))
    const customEntries: CatalogModel[] = customIds.map((id) => ({
      id, context_window: null, tool_use: null, category: "chat", family: "?",
      unknown: true, is_free: null, price_prompt: null, price_completion: null,
    }))
    const catalog = [...live, ...customEntries]
    return { models: catalog.map((m) => m.id), catalog, default_model: cfg.default_model }
  },
}

export interface McpServerBrief {
  id: string
  name: string
  enabled: boolean
  connected: boolean
}

export const mcpInfoApi = {
  list: () => api.get<McpServerBrief[]>("/mcp/servers"),
}
