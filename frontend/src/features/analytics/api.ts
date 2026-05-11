import { api } from "@/shared/api-client"
import type { AnalyticsTotals } from "@/features/dashboard/api"

export interface LlmCallRow {
  id: string
  created_at: string
  model: string
  provider: string
  temperature: number | null
  max_tokens: number | null
  reasoning_effort: string | null
  prompt_tokens: number | null
  completion_tokens: number | null
  cache_read_tokens: number | null
  cache_creation_tokens: number | null
  stop_reason: string | null
  ttft_ms: number | null
  total_ms: number | null
  cost_micros: number | null
  turn_in_session: number | null
  agent_id: string | null
  user_id: string | null
  session_id: string
}

export interface ToolCallRow {
  id: string
  created_at: string
  tool_name: string
  status: string
  duration_ms: number | null
  tool_use_id: string | null
  iteration: number | null
  arguments_size_bytes: number | null
  result_size_bytes: number | null
  result_truncated: boolean | null
  truncate_limit_chars: number | null
  error_type: string | null
  error_message: string | null
  arguments_preview: string | null
  result_preview: string | null
}

export interface CompactionRow {
  id: string
  created_at: string
  triggered_by: string | null
  trigger_threshold_pct: number | null
  model: string | null
  source: string | null
  skipped: number
  skip_reason: string | null
  messages_total: number | null
  messages_visible_before: number | null
  messages_to_summarize: number | null
  messages_kept: number | null
  tokens_before: number | null
  tokens_after_estimate: number | null
  summary_chars: number | null
  duration_ms: number | null
  error: string | null
}

export interface ErrorRow {
  id: string
  created_at: string
  source: string
  severity: string
  error_type: string | null
  error_message: string | null
  traceback: string | null
  context: string | null
}

export interface SessionDetail {
  session: {
    id: string
    title: string | null
    agent_id: string | null
    agent_name: string | null
    user_id: string | null
    project_id: string | null
    status: string
    created_at: string
    updated_at: string
  }
  metrics: AnalyticsTotals & {
    tool_successes?: number
    tool_truncates?: number
    tool_total_ms?: number
    compactions_skipped?: number
    total_llm_ms?: number
  } | null
  llm_calls: LlmCallRow[]
  tool_calls: ToolCallRow[]
  compactions: CompactionRow[]
  errors: ErrorRow[]
}

export const analyticsApi = {
  sessionDetail: (sid: string) => api.get<SessionDetail>(`/analytics/session/${sid}`),
}
