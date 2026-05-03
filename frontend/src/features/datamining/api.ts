import { api } from "@/shared/api-client"
import type { DmEvent, DmSession, DmSessionDetail } from "./types"

export interface SearchParams {
  q: string
  event_type?: string
  agent_name?: string
  username?: string
  from_date?: string
  to_date?: string
  semantic?: boolean
  limit?: number
}

export const dataminingApi = {
  events: (limit = 100) =>
    api.get<{ active: boolean; events: DmEvent[] }>(`/datamining/events?limit=${limit}`),

  search: (p: SearchParams) => {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(p)) {
      if (v !== undefined && v !== "" && v !== null && v !== false) {
        qs.set(k, String(v))
      }
    }
    if (p.semantic) qs.set("semantic", "true")
    return api.get<{ active: boolean; results: DmEvent[]; error: string | null }>(
      `/datamining/search?${qs}`
    )
  },

  sessions: (agent_name?: string, username?: string, limit = 50) => {
    const qs = new URLSearchParams({ limit: String(limit) })
    if (agent_name) qs.set("agent_name", agent_name)
    if (username) qs.set("username", username)
    return api.get<{ active: boolean; sessions: DmSession[] }>(`/datamining/sessions?${qs}`)
  },

  sessionDetail: (id: string) =>
    api.get<DmSessionDetail>(`/datamining/sessions/${id}`),

  embedStatus: () =>
    api.get<{
      active: boolean
      total: number
      embedded: number
      pending: number
      model: string
      backfill_running: boolean
    }>("/datamining/embed/status"),

  triggerBackfill: () =>
    api.post<{ ok: boolean; reason?: string; model?: string }>("/datamining/embed/backfill", {}),
}
