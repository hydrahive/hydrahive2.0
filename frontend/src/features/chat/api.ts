import { useAuthStore } from "@/features/auth/useAuthStore"
import { api } from "@/shared/api-client"
import type { AgentBrief, Message, RunnerEvent, Session } from "./types"

export interface ProjectBrief {
  id: string
  name: string
  agent_id: string
  status: string
}

export const chatApi = {
  listSessions: () => api.get<Session[]>("/sessions"),
  getSession: (id: string) => api.get<Session>(`/sessions/${id}`),
  createSession: (agent_id: string, title?: string, project_id?: string) =>
    api.post<Session>("/sessions", { agent_id, title, project_id }),
  deleteSession: (id: string) => api.delete<void>(`/sessions/${id}`),
  updateSession: (id: string, fields: { title?: string; status?: string }) =>
    api.patch<Session>(`/sessions/${id}`, fields),
  listMessages: (id: string) => api.get<Message[]>(`/sessions/${id}/messages`),
  listAgents: () => api.get<AgentBrief[]>("/agents"),
  listProjects: () => api.get<ProjectBrief[]>("/projects"),
  compact: (id: string) => api.post<{
    skipped?: boolean
    reason_code?: string
    reason_params?: Record<string, unknown>
    summarized_count?: number
    kept_count?: number
    tokens_before?: number
  }>(`/sessions/${id}/compact`, {}),
  tokens: (id: string) => api.get<{
    used: number
    context_window: number
    compact_threshold: number
    model: string | null
  }>(`/sessions/${id}/tokens`),
}

/** Stream a user message through SSE and yield runner events as they arrive. */
export async function* sendMessage(
  sessionId: string,
  text: string,
  signal?: AbortSignal,
): AsyncIterable<RunnerEvent> {
  const token = useAuthStore.getState().token
  const res = await fetch(`/api/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ text }),
    signal,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  if (!res.body) throw new Error("Kein Response-Body")

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const frames = buffer.split("\n\n")
    buffer = frames.pop() ?? ""

    for (const frame of frames) {
      const event = parseSseFrame(frame)
      if (event) yield event
    }
  }
}

function parseSseFrame(frame: string): RunnerEvent | null {
  let data = ""
  for (const line of frame.split("\n")) {
    if (line.startsWith("data: ")) data += line.slice(6)
  }
  if (!data) return null
  try {
    return JSON.parse(data) as RunnerEvent
  } catch {
    return null
  }
}
