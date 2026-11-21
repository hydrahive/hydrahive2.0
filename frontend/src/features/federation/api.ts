import { api } from "@/shared/api-client"
import type {
  A2ACard, ClientConnection, CreateClientResult, Workstation,
  ExternalInstance, CreateInstanceResult, Peer, PeerIdentity, PeerOwnCode,
  CatalogSettings,
} from "./types"

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

export const clientsApi = {
  list: (): Promise<ClientConnection[]> =>
    api.get("/federation/clients"),

  create: (name: string): Promise<CreateClientResult> =>
    api.post("/federation/clients", { name }),

  delete: (keyId: string): Promise<void> =>
    api.delete(`/federation/clients/${keyId}`),
}

export const externalInstancesApi = {
  list: (): Promise<ExternalInstance[]> =>
    api.get("/external-instances"),

  create: (name: string, llm_model: string): Promise<CreateInstanceResult> =>
    api.post("/external-instances", { name, llm_model }),

  rotateKey: (agentId: string): Promise<{ api_key: string }> =>
    api.post(`/external-instances/${agentId}/rotate-key`, {}),
}

export const peersApi = {
  identity: (): Promise<PeerIdentity> =>
    api.get("/federation/peers/identity"),

  ownCode: (name: string, url: string): Promise<PeerOwnCode> =>
    api.post("/federation/peers/identity/code", { name, url }),

  list: (): Promise<Peer[]> =>
    api.get("/federation/peers"),

  add: (code: string): Promise<Peer> =>
    api.post("/federation/peers", { code }),

  confirm: (id: string, fingerprint: string): Promise<Peer> =>
    api.post(`/federation/peers/${id}/confirm`, { fingerprint }),

  block: (id: string): Promise<Peer> =>
    api.post(`/federation/peers/${id}/block`, {}),

  delete: (id: string): Promise<void> =>
    api.delete(`/federation/peers/${id}`),

  setAgents: (id: string, agent_ids: string[]): Promise<Peer> =>
    api.put(`/federation/peers/${id}/agents`, { agent_ids }),

  // Föderations-Katalog (docs/specs/federation-catalog.md, Etappe 1): Hub-Markierung und Annahme.
  setHub: (id: string, is_hub: boolean): Promise<Peer> =>
    api.put(`/federation/peers/${id}/hub`, { is_hub }),

  setCatalogAccept: (id: string, accept: boolean): Promise<Peer> =>
    api.put(`/federation/peers/${id}/catalog`, { accept }),
}

export interface CatalogSettingsPatch {
  enabled: boolean
  interval_seconds: number
  users: string[]
  excluded_projects: string[]
}

export const catalogApi = {
  getSettings: (): Promise<CatalogSettings> =>
    api.get("/federation/catalog/settings"),

  saveSettings: (body: CatalogSettingsPatch): Promise<CatalogSettings> =>
    api.put("/federation/catalog/settings", body),

  /** Voller Abgleich sofort (Etappe 3). ``result``: ok · inactive · Fehlercode des Laufs. */
  syncNow: (): Promise<{ result: string; settings: CatalogSettings }> =>
    api.post("/federation/catalog/sync-now", {}),
}
