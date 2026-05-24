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
