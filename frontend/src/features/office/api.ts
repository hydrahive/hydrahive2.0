import { api } from "@/shared/api-client"

export interface AgentTraceCall {
  id: string
  tool_name: string
  status: string
  duration_ms: number | null
  created_at: string
  iteration: number | null
  // Etappe 5 (Spec agent-office.md §8.2): Kurzfassung + erkannter PR-/Issue-Link.
  result_summary?: string
  github_link?: string | null
}

export interface AgentTrace {
  session_id: string
  calls: AgentTraceCall[]
}

/** Live-Tool-Verlauf einer Agenten-Session für den Drawer (Spec agent-office.md §2). */
export async function fetchAgentTrace(sessionId: string): Promise<AgentTrace> {
  return api.get<AgentTrace>(`/agents/activity/${sessionId}/trace`)
}
