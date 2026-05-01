import { api } from "@/shared/api-client"
import type { Credential, CredentialSavePayload } from "./types"

export const credentialsApi = {
  list: () => api.get<Credential[]>("/credentials"),
  get: (name: string, reveal = false) =>
    api.get<Credential>(`/credentials/${encodeURIComponent(name)}${reveal ? "?reveal=true" : ""}`),
  save: (payload: CredentialSavePayload) => api.post<Credential>("/credentials", payload),
  remove: (name: string) => api.delete<void>(`/credentials/${encodeURIComponent(name)}`),
}
