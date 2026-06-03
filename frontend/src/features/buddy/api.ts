import { api } from "@/shared/api-client"

export interface BuddyState {
  agent_id: string
  session_id: string
  agent_name: string
  model: string
  project_id: string | null
  created: boolean
}

export interface ClearResult { ok: boolean; session_id: string; message: string }
export interface RememberResult { ok: boolean; key: string; message: string }
export interface ModelsResult { current: string; available: string[] }
export interface SetModelResult { ok: boolean; model: string; message: string }
export interface CharacterResult { ok: boolean; session_id: string; message: string }

export interface BuddyConfig {
  name: string
  model: string
  character: string
  tools: string[]
  all_tools: string[]
  compact_threshold_pct: number
  compact_model: string
  tool_result_max_chars: number
  language: "de" | "en" | "auto"
  tone: "locker" | "professionell" | "knapp"
  context: string
}

export interface BuddyConfigPatch {
  name?: string
  tools?: string[]
  compact_threshold_pct?: number
  compact_model?: string
  tool_result_max_chars?: number
  language?: "de" | "en" | "auto"
  tone?: "locker" | "professionell" | "knapp"
  context?: string
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
