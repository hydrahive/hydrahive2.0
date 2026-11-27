import { api } from "@/shared/api-client"
import type { Agent, AgentCreate, AgentDefaults, AgentTemplate, AgentToolConfig, AgentUpdate, ToolMeta } from "./types"

export const agentsApi = {
  list: () => api.get<Agent[]>("/agents"),
  get: (id: string) => api.get<Agent>(`/agents/${id}`),
  create: (req: AgentCreate) => api.post<Agent>("/agents", req),
  update: (id: string, fields: AgentUpdate) =>
    api.patch<Agent>(`/agents/${id}`, fields),
  getSystemPrompt: (id: string) =>
    api.get<{ prompt: string; source?: "soul" | "prompt" }>(`/agents/${id}/system_prompt`),
  setSystemPrompt: (id: string, prompt: string) =>
    api.put<{ prompt: string }>(`/agents/${id}/system_prompt`, { prompt }),
  getSoul: (id: string) =>
    api.get<{ components: Record<string, string> }>(`/agents/${id}/soul`),
  setSoulComponent: (id: string, component: string, content: string) =>
    api.put<{ component: string; saved: boolean }>(`/agents/${id}/soul/${component}`, { content }),
  getSoulTemplates: (id: string) =>
    api.get<{ templates: Record<string, string>; agent_type: string }>(`/agents/${id}/soul/templates`),
  listTools: () => api.get<ToolMeta[]>("/agents/_meta/tools"),
  getDefaults: () => api.get<AgentDefaults>("/agents/_meta/defaults"),
  listTemplates: () => api.get<AgentTemplate[]>("/agents/_meta/templates"),
}

/** Effektive globale Mail-Config — Platzhalter fürs per-Buddy-Postfach (ohne Passwort). */
export const mailDefaultsApi = {
  get: () => api.get<AgentToolConfig>("/system/mail-defaults"),
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

/** Freigabe-Pool eines Agenten (Katalog): was ihm per ask_agent zugewiesen werden darf. */
export interface AgentToolPool {
  items: string[]
  effective?: string[]
  categories?: string[]
  forbidden?: string[]
}

export const toolPoolApi = {
  get: (agentId: string) => api.get<AgentToolPool>(`/agents/${agentId}/tool-pool`),
  put: (agentId: string, items: string[]) => api.put<{ items: string[] }>(`/agents/${agentId}/tool-pool`, { items }),
}
