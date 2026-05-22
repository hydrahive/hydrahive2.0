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

export interface Workstation {
  id: string
  name: string
  url: string
  has_token: boolean
  enabled: boolean
  last_seen: string | null
  card: A2ACard | null
  created_at: string
}
