import { api } from "@/shared/api-client"

export interface BuddyState {
  agent_id: string
  session_id: string
  agent_name: string
  model: string
  created: boolean
}

export interface ClearResult { ok: boolean; session_id: string; message: string }
export interface RememberResult { ok: boolean; key: string; message: string }
export interface ModelsResult { current: string; available: string[] }
export interface SetModelResult { ok: boolean; model: string; message: string }
export interface CharacterResult { ok: boolean; session_id: string; message: string }

export const buddyApi = {
  state: () => api.get<BuddyState>("/buddy/state"),
  clear: () => api.post<ClearResult>("/buddy/clear", {}),
  remember: (text: string) => api.post<RememberResult>("/buddy/remember", { text }),
  models: () => api.get<ModelsResult>("/buddy/models"),
  setModel: (model: string) => api.post<SetModelResult>("/buddy/model", { model }),
  character: () => api.post<CharacterResult>("/buddy/character", {}),
}
