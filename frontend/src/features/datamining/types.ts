export interface DmEvent {
  id: string
  session_id: string
  username: string | null
  agent_name: string | null
  event_type: string
  created_at: string
  tool_name: string | null
  is_error: boolean | null
  snippet: string | null
  similarity?: number
}

export interface DmSession {
  id: string
  username: string | null
  agent_name: string | null
  project_id: string | null
  title: string | null
  status: string | null
  started_at: string | null
  updated_at: string | null
  event_count: number
}

export interface DmSessionEvent {
  event_type: string
  created_at: string
  username: string | null
  agent_name: string | null
  tool_name: string | null
  tool_use_id: string | null
  tool_input: unknown | null
  is_error: boolean | null
  text?: string
  tool_output?: string
}

export interface DmSessionDetail {
  session: DmSession
  events: DmSessionEvent[]
}

export const TYPE_COLORS: Record<string, string> = {
  user_input:     "text-blue-300 bg-blue-500/10",
  assistant_text: "text-violet-300 bg-violet-500/10",
  tool_call:      "text-amber-300 bg-amber-500/10",
  tool_result:    "text-emerald-300 bg-emerald-500/10",
  thinking:       "text-zinc-400 bg-zinc-500/10",
  compaction:     "text-fuchsia-300 bg-fuchsia-500/10",
}

export function fmtTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString("de", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  } catch {
    return ts.slice(11, 19)
  }
}

export function fmtDateTime(ts: string | null): string {
  if (!ts) return "—"
  try {
    return new Date(ts).toLocaleString("de", { dateStyle: "short", timeStyle: "short" })
  } catch {
    return ts.slice(0, 16)
  }
}
