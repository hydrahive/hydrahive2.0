import { api } from "@/shared/api-client"
import type { AgentToolConfig } from "@/features/agents/types"

export interface BuddyState {
  agent_id: string
  session_id: string
  agent_name: string
  model: string
  project_id: string | null
  created: boolean
}

export interface BuddyToolMeta {
  name: string
  description: string
  category?: string | null
}

export type BuddyLanguage = "de" | "en" | "auto"
export type BuddyTone = "locker" | "professionell" | "knapp"
export type ReasoningEffort = "" | "low" | "medium" | "high"
export type CacheTtl = "5m" | "1h"

export interface ClearResult { ok: boolean; session_id: string; message: string }
export interface RememberResult { ok: boolean; key: string; message: string }
export interface ModelsResult { current: string; available: string[] }
export interface SetModelResult { ok: boolean; model: string; message: string }
export interface CharacterResult { ok: boolean; session_id: string; message: string }

export interface BuddyConfig {
  agent_id: string
  name: string
  model: string
  fallback_models: string[]
  temperature: number
  max_tokens: number
  thinking_budget: number
  reasoning_effort: ReasoningEffort
  character: string
  tools: string[]
  all_tools: string[]
  available_tools: BuddyToolMeta[]
  mcp_servers: string[]
  disabled_skills: string[]
  require_tool_confirm: boolean
  longterm_memory: boolean
  compact_threshold_pct: number
  compact_model: string
  compact_tool_result_limit: number
  compact_reserve_tokens: number
  compact_max_turns: number | null
  tool_result_max_chars: number
  max_iterations: number
  cache_ttl: CacheTtl
  language: BuddyLanguage
  tone: BuddyTone
  context: string
  tool_config?: AgentToolConfig
}

export interface BuddyConfigPatch {
  name?: string
  model?: string
  fallback_models?: string[]
  temperature?: number
  max_tokens?: number
  thinking_budget?: number
  reasoning_effort?: ReasoningEffort
  tools?: string[]
  mcp_servers?: string[]
  disabled_skills?: string[]
  require_tool_confirm?: boolean
  longterm_memory?: boolean
  compact_threshold_pct?: number
  compact_model?: string
  compact_tool_result_limit?: number
  compact_reserve_tokens?: number
  compact_max_turns?: number | null
  tool_result_max_chars?: number
  max_iterations?: number
  cache_ttl?: CacheTtl
  language?: BuddyLanguage
  tone?: BuddyTone
  context?: string
  tool_config?: AgentToolConfig
}

export interface PatchResult { ok: boolean; new_session_id: string | null }

export const buddyApi = {
  state: () => api.get<BuddyState>("/buddy/state"),
  clear: () => api.post<ClearResult>("/buddy/clear", {}),
  remember: (body: { text?: string; name?: string }) =>
    api.post<RememberResult>("/buddy/remember", body),
  models: () => api.get<ModelsResult>("/buddy/models"),
  setModel: (model: string) => api.post<SetModelResult>("/buddy/model", { model }),
  character: () => api.post<CharacterResult>("/buddy/character", {}),
  logCmd: (user_text: string, assistant_text: string) =>
    api.post<{ ok: boolean }>("/buddy/log-cmd", { user_text, assistant_text }),
  getConfig: () => api.get<BuddyConfig>("/buddy/config"),
  patchConfig: (patch: BuddyConfigPatch) => api.patch<PatchResult>("/buddy/config", patch),
}
