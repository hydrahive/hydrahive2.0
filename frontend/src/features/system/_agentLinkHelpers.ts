export interface KnownAgent {
  agent_id: string
  last_seen: string
  states: number
}

export interface AgentLinkStatus {
  configured: boolean
  connected: boolean
  ws_connected?: boolean
  backend_reachable?: boolean
  last_error?: string | null
  url?: string
  ws_url?: string
  agent_id?: string
  handoff_timeout_s?: number
  known_agents?: KnownAgent[]
  reconnect_attempts?: number
  last_connect_at?: string | null
  pending_handoffs?: number
  dashboard_url?: string
}

export function relTime(iso: string, locale: string): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (isNaN(d.getTime())) return "—"
  const diffMs = Date.now() - d.getTime()
  const s = Math.round(diffMs / 1000)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.round(s / 60)}m`
  if (s < 86400) return `${Math.round(s / 3600)}h`
  return d.toLocaleDateString(locale)
}
