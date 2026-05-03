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

  resetEmbeddings: (event_type?: string) => {
    const qs = event_type ? `?event_type=${event_type}` : ""
    return api.post<{ ok: boolean; reset: number }>(`/datamining/embed/reset${qs}`, {})
  },

  startExport: () =>
    api.post<{ ok: boolean; reason?: string }>("/datamining/export", {}),

  downloadExport: async (filename: string) => {
    const { useAuthStore } = await import("@/features/auth/useAuthStore")
    const token = useAuthStore.getState().token
    const res = await fetch("/api/datamining/export/download", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error("Download fehlgeschlagen")
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
  },

  exportStatus: () =>
    api.get<{ running: boolean; done: boolean; filename: string | null; size_mb: number; error: string | null }>(
      "/datamining/export/status"
    ),

  startImport: (file: File) => {
    const form = new FormData()
    form.append("file", file)
    return api.postForm<{ ok: boolean; reason?: string }>("/datamining/import", form)
  },

  importStatus: () =>
    api.get<{ running: boolean; done: boolean; error: string | null }>("/datamining/import/status"),
}
