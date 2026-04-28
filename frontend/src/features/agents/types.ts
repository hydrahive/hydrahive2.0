export interface Agent {
  id: string
  type: "master" | "project" | "specialist"
  name: string
  owner: string | null
  created_by: string | null
  llm_model: string
  tools: string[]
  mcp_servers: string[]
  description: string
  temperature: number
  max_tokens: number
  thinking_budget: number
  status: "active" | "disabled"
  created_at: string
  updated_at: string
  project_id?: string | null
  domain?: string | null
}

export interface ToolMeta {
  name: string
  description: string
}

export interface AgentDefaults {
  tools_per_type: Record<string, string[]>
  types: string[]
}

export interface AgentCreate {
  type: string
  name: string
  llm_model: string
  tools: string[]
  description: string
  temperature: number
  max_tokens: number
  thinking_budget: number
  mcp_servers: string[]
  owner?: string | null
  domain?: string | null
  system_prompt?: string | null
}
