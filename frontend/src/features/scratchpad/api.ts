import { api } from "@/shared/api-client"

export interface ScratchpadData {
  user_content: string
  agent_content: string
}

export const scratchpadApi = {
  get: () => api.get<ScratchpadData>("/scratchpad"),
  saveUser: (content: string) => api.put<{ saved: boolean }>("/scratchpad", { content }),
  clearAgent: () => api.delete<{ cleared: boolean }>("/scratchpad/agent"),
}
