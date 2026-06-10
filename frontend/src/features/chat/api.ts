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
  createSession: (agent_id: string, title?: string, project_id?: string) =>
    api.post<Session>("/sessions", { agent_id, title, project_id }),
  deleteSession: (id: string) => api.delete<void>(`/sessions/${id}`),
  updateSession: (id: string, fields: { title?: string; status?: string; model_override?: string | null; reasoning_effort?: string | null; project_id?: string | null }) =>
    api.patch<Session>(`/sessions/${id}`, fields),
  listMessages: (id: string) => api.get<Message[]>(`/sessions/${id}/messages`),
  logCmd: (id: string, user_text: string, assistant_text: string) =>
    api.post<{ ok: boolean }>(`/sessions/${id}/log-cmd`, { user_text, assistant_text }),
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
    message_count?: number
    max_turns?: number
  }>(`/sessions/${id}/tokens`),
  toolConfirm: (sessionId: string, callId: string, decision: "approve" | "deny") =>
    api.post<{ resolved: boolean }>(`/sessions/${sessionId}/tool-confirm/${callId}`, { decision }),
}

/** Stream a user message through SSE and yield runner events as they arrive. */
export async function* sendMessage(
  sessionId: string,
  text: string,
  files: File[] = [],
  signal?: AbortSignal,
  resendMessageId?: string,
): AsyncIterable<RunnerEvent> {
  const token = useAuthStore.getState().token
  const body = new FormData()
  body.append("text", text)
  for (const file of files) body.append("files", file, file.name)
  // local-* IDs existieren nur im Frontend-State, nie in der DB → als neue Nachricht senden
  const effectiveResendId = resendMessageId?.startsWith("local-") ? undefined : resendMessageId
  const url = effectiveResendId
    ? `/api/sessions/${sessionId}/messages/${encodeURIComponent(effectiveResendId)}/resend`
    : `/api/sessions/${sessionId}/messages`
  const res = await fetch(url, {
    method: "POST",
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body,
    signal,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = body.detail
    const msg = res.status === 409
      ? "Agent läuft noch – bitte kurz warten"
      : typeof detail === "string" ? detail : (detail?.code ?? `HTTP ${res.status}`)
    throw new Error(msg)
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

/**
 * Live-Sync v1: abonniert den Session-Broadcast-Kanal. Ruft `onPing` bei jedem
 * Aktivitäts-Ping (ein Lauf macht Fortschritt). Läuft bis `signal` abbricht und
 * reconnectet bei Verbindungsabriss. EventSource scheidet aus (kann keinen
 * Authorization-Header), darum fetch + getReader wie bei sendMessage.
 */
export async function subscribeSession(
  sessionId: string,
  onPing: () => void,
  signal: AbortSignal,
): Promise<void> {
  const RECONNECT_MS = 1500
  while (!signal.aborted) {
    try {
      const token = useAuthStore.getState().token
      const res = await fetch(`/api/sessions/${sessionId}/stream`, {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        signal,
      })
      if (!res.ok || !res.body) throw new Error(`stream ${res.status}`)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const frames = buffer.split("\n\n")
        buffer = frames.pop() ?? ""
        // Ein Frame mit data:-Zeile = Ping (Keepalive sind reine :-Kommentare).
        for (const frame of frames) {
          if (frame.split("\n").some((l) => l.startsWith("data:"))) onPing()
        }
      }
    } catch {
      if (signal.aborted) return
    }
    if (signal.aborted) return
    await new Promise((r) => setTimeout(r, RECONNECT_MS))
  }
}
