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

// --- Analytics (Token-Audit #130) ------------------------------------------

export interface AnalyticsTotals {
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_creation_tokens?: number
  cost_micros: number
  llm_calls: number
  tool_calls?: number
  tool_errors?: number
  compactions?: number
  errors: number
  sessions: number
}

export interface AnalyticsTopSession {
  session_id: string
  agent_id: string
  title: string | null
  created_at: string
  cost_micros: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  llm_calls: number
  tool_calls: number
  errors: number
}

export interface AnalyticsByModel {
  model: string
  calls: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cost_micros: number
}

export interface AnalyticsOverview {
  today: AnalyticsTotals
  last_7d: AnalyticsTotals
  top_cost_sessions: AnalyticsTopSession[]
  by_model: AnalyticsByModel[]
}

export const analyticsApi = {
  overview: () => api.get<AnalyticsOverview>("/analytics/overview"),
}
