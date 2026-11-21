export interface A2ACapabilities {
  a2a: boolean
  streaming: boolean
  tools: boolean
  chat: boolean
  shell: boolean
}

export interface A2AAgent {
  id: string
  name: string
  description?: string
  type: string
}

export interface A2ACard {
  name: string
  description: string
  url: string
  version: string
  commit?: string
  protocol: string
  capabilities: A2ACapabilities
  agents: A2AAgent[]
  endpoints?: Record<string, string>
}

export interface ClientConnection {
  id: string
  name: string
  username: string
  role: string
  created_at: string
}

export interface ClientConfig {
  schema: string
  name: string
  generated_at: string
  hh2: {
    api_url: string | null
    api_url_dns: string | null
    api_key: string
  }
  agentlink: {
    url: string | null
    ws_url: string | null
    agent_id: string
  } | null
  tailscale: {
    ip: string | null
    hostname: string | null
    dns_name: string | null
    authkey: string | null
  } | null
}

export interface CreateClientResult {
  key_id: string
  name: string
  config: ClientConfig
}

export interface Workstation {
  id: string
  name: string
  url: string
  has_token: boolean
  enabled: boolean
  /**
   * Per-workstation TLS-cert-verify flag. Set to false for self-
   * signed peers (typical for LAN/Tailnet setups). Backend default
   * is true (verify on).
   */
  verify_tls: boolean
  last_seen: string | null
  card: A2ACard | null
  created_at: string
}

export interface ExternalInstance {
  agent_id: string
  name: string
  username: string
  key_count: number
  session_count: number
  last_activity: string | null
}

export interface CreateInstanceResult {
  username: string
  agent_id: string
  api_key: string
}

// Server-Kopplung HydraHive ↔ HydraHive (docs/specs/server-peering.md)
export type PeerStatus = "pending" | "active" | "blocked"

export interface Peer {
  id: string
  name: string
  url: string
  fingerprint: string
  status: PeerStatus
  created_at: string
  confirmed_at: string | null
  last_seen: string | null
  allowed_agents: string[]
  /** Föderations-Katalog (docs/specs/federation-catalog.md): dieser Partner ist der Hub. Höchstens einer. */
  is_hub: boolean
  /** Dieser Server nimmt vom Partner den Katalog an (Partner = Sender, dieser Server = Empfänger/Hub für ihn). */
  catalog_accept: boolean
}

/** Einstellungen des Föderations-Katalogs (docs/specs/federation-catalog.md §API). */
export interface CatalogSettings {
  enabled: boolean
  interval_seconds: number
  users: string[]
  excluded_projects: string[]
  hub: { id: string; name: string; status: PeerStatus } | null
  /** Partner, für die dieser Server selbst als Hub Katalog-Daten annimmt (catalog_accept=1 beim Partner). */
  accepting_from: { id: string; name: string }[]
  last_push_at: string | null
  last_ok_at: string | null
  last_full_at: string | null
  last_error: string | null
}

export interface PeerIdentity {
  fingerprint: string
  /** Tailscale-Name + -Adresse dieses Servers; null ohne verbundenes Tailscale. */
  suggested: { name: string; url: string } | null
}

export interface PeerOwnCode {
  code: string
  fingerprint: string
}
