import { api } from "@/shared/api-client"

export interface DashboardStats {
  active_sessions: number
  tokens_today: number
  tool_calls_today: number
  servers_running: number
  servers_total: number
}

export interface DashboardSession {
  id: string
  title: string
  agent_id: string
  agent_name: string
  agent_type: string | null
  status: string
  updated_at: string
  project_id: string | null
}

export interface DashboardServer {
  kind: "vm" | "container"
  id: string
  name: string
  actual_state: string
  project_id: string | null
}

export interface DashboardAgent {
  id: string
  type: string
  name: string
  owner: string | null
  project_id: string | null
  status: string
}

export interface DashboardHealth {
  backend: { ok: boolean }
  agentlink: { ok: boolean; configured: boolean }
  bridge: { ok: boolean }
  tailscale: { ok: boolean; configured: boolean }
}

export interface DashboardSummary {
  health: DashboardHealth
  stats: DashboardStats
  recent_sessions: DashboardSession[]
  servers: DashboardServer[]
  agents: DashboardAgent[]
  version: { commit: string | null; update_behind: number | null }
}

export const dashboardApi = {
  summary: () => api.get<DashboardSummary>("/dashboard"),
}
