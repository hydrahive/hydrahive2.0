import { api } from "@/shared/api-client"
import type { AreaCatalog, AreaStatus, Suggestion } from "./types"

export const areasApi = {
  catalog: (lang: string) => api.get<AreaCatalog>(`/agent-areas?lang=${encodeURIComponent(lang)}`),
  status: (agentId: string) => api.get<AreaStatus>(`/agents/${agentId}/areas`),
  suggest: (agentId: string, purpose: string, lang: string) =>
    api.post<{ suggestions: Suggestion[]; error?: string }>(`/agents/${agentId}/area-suggestion`, { purpose, lang }),
}
