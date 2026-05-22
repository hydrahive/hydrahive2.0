import { api } from "@/shared/api-client"
import type { A2ACard, Workstation } from "./types"

export const federationApi = {
  list: (): Promise<Workstation[]> =>
    api.get("/federation/workstations"),

  create: (name: string, url: string, token: string, enabled = true): Promise<Workstation> =>
    api.post("/federation/workstations", { name, url, token, enabled }),

  update: (id: string, fields: Partial<{ name: string; url: string; token: string; enabled: boolean }>): Promise<Workstation> =>
    api.put(`/federation/workstations/${id}`, fields),

  delete: (id: string): Promise<void> =>
    api.delete(`/federation/workstations/${id}`),

  refresh: (id: string): Promise<A2ACard> =>
    api.post(`/federation/workstations/${id}/refresh`, {}),

  audit: (id: string): Promise<unknown[]> =>
    api.get(`/federation/workstations/${id}/audit`),
}
