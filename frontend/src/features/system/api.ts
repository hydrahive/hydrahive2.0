import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"

export interface SystemInfo {
  version: string
  started_at: number
  uptime_seconds: number
  python: string
  platform: string
  data_dir: string
  config_dir: string
  db_path: string
  db_size_bytes: number
}

export interface SystemStats {
  agents: { total: number; by_type: Record<string, number> }
  projects: { total: number; active: number }
  sessions: { total: number; active: number }
  messages: { total: number; compactions: number }
  tool_calls: {
    total: number
    success: number
    error: number
    success_rate: number
  }
}

export interface HealthCheck {
  name_code?: string
  detail_code?: string
  params?: Record<string, unknown>
  name?: string
  detail?: string
  ok: boolean
}

export const systemApi = {
  info: () => api.get<SystemInfo>("/system/info"),
  stats: () => api.get<SystemStats>("/system/stats"),
  health: () => api.get<{ checks: HealthCheck[] }>("/system/health"),
  installVoice: () => api.post<{ started: boolean }>("/system/install-voice", {}),
  voiceLog: (tail = 300) => api.get<{ lines: string[]; exists: boolean }>(`/system/install-voice/log?tail=${tail}`),
  bridgeStatus: () => api.get<{ installed: boolean; state?: string; ip?: string }>("/system/bridge/status"),
  bridgeSetup: () => api.post<{ started: boolean }>("/system/bridge/setup", {}),
  bridgeLog: (tail = 200) =>
    api.get<{ lines: string[]; exists: boolean }>(`/system/bridge/log?tail=${tail}`),
  downloadBackup: async () => {
    const token = useAuthStore.getState().token || ""
    const r = await fetch("/api/admin/backup", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const cd = r.headers.get("content-disposition") || ""
    const m = /filename="?([^"]+)"?/.exec(cd)
    const filename = m?.[1] || "hydrahive2-backup.tar.gz"
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },
  restoreBackup: async (file: File) => {
    const token = useAuthStore.getState().token || ""
    const fd = new FormData()
    fd.append("archive", file)
    const r = await fetch("/api/admin/restore", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    })
    if (!r.ok) {
      const text = await r.text()
      try {
        const json = JSON.parse(text)
        throw json
      } catch {
        throw new Error(text || `HTTP ${r.status}`)
      }
    }
    return r.json()
  },
}
