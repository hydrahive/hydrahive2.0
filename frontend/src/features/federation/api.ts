import { api } from "@/shared/api-client"
import type { A2ACard, Workstation } from "./types"

// All optional fields a workstation can have. Keeping it as a type
// alias means create() and update() share the exact same shape.
export interface WorkstationFields {
  name?: string
  url?: string
  token?: string
  enabled?: boolean
  /**
   * When false, the HH2 registry skips TLS-cert verification for
   * this workstation. Set to false for self-signed LAN/Tailnet
   * peers (e.g. ProjektX behind --tls-auto). Defaults to true.
   */
  verify_tls?: boolean
}

export const federationApi = {
  list: (): Promise<Workstation[]> =>
    api.get("/federation/workstations"),

  create: (
    name: string,
    url: string,
    token: string,
    opts: { enabled?: boolean; verify_tls?: boolean } = {},
  ): Promise<Workstation> =>
    api.post("/federation/workstations", {
      name,
      url,
      token,
      enabled: opts.enabled ?? true,
      verify_tls: opts.verify_tls ?? true,
    }),

  update: (id: string, fields: WorkstationFields): Promise<Workstation> =>
    api.put(`/federation/workstations/${id}`, fields),

  delete: (id: string): Promise<void> =>
    api.delete(`/federation/workstations/${id}`),

  refresh: (id: string): Promise<A2ACard> =>
    api.post(`/federation/workstations/${id}/refresh`, {}),

  audit: (id: string): Promise<unknown[]> =>
    api.get(`/federation/workstations/${id}/audit`),
}
