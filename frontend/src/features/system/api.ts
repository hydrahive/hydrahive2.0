import { api } from "@/shared/api-client"

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
}
