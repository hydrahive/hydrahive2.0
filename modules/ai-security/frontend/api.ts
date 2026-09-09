import { api } from "@/shared/api-client"

const BASE = "/modules/ai-security"

export interface AISecurityHealth {
  configured: boolean
  reachable: boolean
  error: string | null
}

export interface AISecurityScan {
  id: string
  username: string
  scan_type: "infra"
  target_url: string
  upstream_session_id: string | null
  status: "queued" | "running" | "completed" | "failed"
  result: Record<string, unknown> | null
  error_code: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

export const aiSecurityApi = {
  health: () => api.get<AISecurityHealth>(`${BASE}/health`),
  targets: () => api.get<string[]>(`${BASE}/targets`),
  scans: () => api.get<AISecurityScan[]>(`${BASE}/scans`),
  createScan: (target_url: string) =>
    api.post<AISecurityScan>(`${BASE}/scans`, { scan_type: "infra", target_url }),
  scan: (id: string) => api.get<AISecurityScan>(`${BASE}/scans/${encodeURIComponent(id)}`),
}
