import { api } from "@/shared/api-client"
import type {
  MemoryResponse, CrystalsResponse,
  MemorySessionsResponse, ObservationsResponse,
} from "./types"

export const memoryApi = {
  getMemory: (agentId: string, params?: { project?: string; q?: string; include_expired?: boolean; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.project) qs.set("project", params.project)
    if (params?.q) qs.set("q", params.q)
    if (params?.include_expired) qs.set("include_expired", "true")
    if (params?.limit) qs.set("limit", String(params.limit))
    const query = qs.toString()
    return api.get<MemoryResponse>(`/agents/${agentId}/memory${query ? "?" + query : ""}`)
  },

  deleteEntry: (agentId: string, key: string) =>
    api.delete<void>(`/agents/${agentId}/memory/${encodeURIComponent(key)}`),

  getCrystals: (agentId: string, params?: { project?: string; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.project) qs.set("project", params.project)
    if (params?.limit) qs.set("limit", String(params.limit))
    const query = qs.toString()
    return api.get<CrystalsResponse>(`/agents/${agentId}/crystals${query ? "?" + query : ""}`)
  },

  getSessions: (agentId: string, params?: { project?: string; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.project) qs.set("project", params.project)
    if (params?.limit) qs.set("limit", String(params.limit))
    const query = qs.toString()
    return api.get<MemorySessionsResponse>(`/agents/${agentId}/memory-sessions${query ? "?" + query : ""}`)
  },

  getObservations: (agentId: string, sessionId: string) =>
    api.get<ObservationsResponse>(`/agents/${agentId}/memory-sessions/${sessionId}/observations`),
}
