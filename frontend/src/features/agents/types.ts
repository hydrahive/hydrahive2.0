export interface Agent {
  id: string
  type: "master" | "project" | "specialist"
  name: string
  owner: string | null
  created_by: string | null
  llm_model: string
  fallback_models: string[]
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
  // Per-Agent Compaction-Settings (#82). Alle optional, Backend backfillt
  // Defaults bei alten Agents.
  compact_model?: string         // "" = main llm_model
  compact_tool_result_limit?: number
  compact_reserve_tokens?: number
  compact_threshold_pct?: number
  workspace?: string
  disabled_skills?: string[]
}

export interface ToolMeta {
  name: string
  description: string
  category?: string
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
  fallback_models: string[]
  owner?: string | null
  domain?: string | null
  system_prompt?: string | null
  compact_model?: string
  compact_tool_result_limit?: number
  compact_reserve_tokens?: number
  compact_threshold_pct?: number
}
