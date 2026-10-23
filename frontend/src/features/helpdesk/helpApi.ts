// Hilfe-Assistent (docs/plans/help-assistant.md): Zustand holen, Nachricht senden (mit aktueller Seite), Verlauf.
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { Message, RunnerEvent } from "@/features/chat/types"
import { api } from "@/shared/api-client"

export interface HelpState {
  model_missing: boolean
  agent_id: string | null
  session_id: string | null
  created: boolean
}

export const helpApi = {
  state: () => api.get<HelpState>("/helpdesk/state"),
  messages: (sessionId: string) => api.get<Message[]>(`/sessions/${sessionId}/messages?limit=60`),
}

export class HelpSendError extends Error {
  code?: string
  constructor(message: string, code?: string) {
    super(message)
    this.code = code
  }
}

/** Sendet eine Frage und liefert die Ereignisse des Laufs (SSE), wie der normale Chat. */
export async function* sendHelpMessage(sessionId: string, text: string, path: string, signal?: AbortSignal):
    AsyncIterable<RunnerEvent> {
  const token = useAuthStore.getState().token
  const res = await fetch("/api/helpdesk/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ session_id: sessionId, text, path }),
    signal,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const code = typeof body?.detail === "object" ? body.detail?.code : undefined
    throw new HelpSendError(code ?? `HTTP ${res.status}`, code)
  }
  if (!res.body) return
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
      const data = frame.split("\n").filter((l) => l.startsWith("data: ")).map((l) => l.slice(6)).join("")
      if (!data) continue
      try { yield JSON.parse(data) as RunnerEvent } catch { /* unvollständiger Frame */ }
    }
  }
}

const OPEN_KEY = "hh-help-open"

/** Offen/zu je Browser-Tab merken – beim Neuladen bleibt das Fenster, wie es war. */
export function readOpen(): boolean {
  try { return sessionStorage.getItem(OPEN_KEY) === "1" } catch { return false }
}

export function writeOpen(open: boolean): void {
  try { sessionStorage.setItem(OPEN_KEY, open ? "1" : "0") } catch { /* privater Modus */ }
}
