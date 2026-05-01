import { api } from "@/shared/api-client"

export interface BuddyState {
  agent_id: string
  session_id: string
  agent_name: string
  model: string
  created: boolean
}

export const buddyApi = {
  state: () => api.get<BuddyState>("/buddy/state"),
}
