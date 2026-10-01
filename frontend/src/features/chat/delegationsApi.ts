import { api } from "@/shared/api-client"

/** Hintergrund-Auftrag an einen Spezialisten (docs/specs/agent-background-delegation.md). */
export interface Delegation {
  id: string
  target_agent_id: string
  target_name: string
  task: string
  status: "running" | "done" | "error" | "paused" | "timeout" | "cancelled" | "lost"
  depth: number
  created_at: string
  deadline_at: string
  finished_at: string | null
  delivered: boolean
  target_session_id: string | null
  rounds: number | null
  current_tool: string | null
}

export interface DelegationList {
  delegations: Delegation[]
  undelivered: boolean
  paused: boolean
}

export const delegationsApi = {
  list: (sessionId: string) => api.get<DelegationList>(`/sessions/${sessionId}/delegations`),
  cancel: (sessionId: string, delegationId: string) =>
    api.post<{ cancelled: boolean }>(`/sessions/${sessionId}/delegations/${delegationId}/cancel`, {}),
  deliver: (sessionId: string) =>
    api.post<{ started: boolean }>(`/sessions/${sessionId}/delegations/deliver`, {}),
}

/** Metadaten der automatischen Ergebnis-Nachricht (runner/_delegation_message.py). */
export interface DelegationResultMeta {
  source: "delegation_result"
  delegations: { id: string; target_name: string; status: Delegation["status"] }[]
}

export function isDelegationResult(metadata: Record<string, unknown> | undefined): boolean {
  return metadata?.source === "delegation_result"
}
