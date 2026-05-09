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
  tool_result_max_chars?: number  // 0 = kein Limit; live-truncation vor LLM-Call
  cache_ttl?: string              // "5m" | "1h" — Anthropic Prompt-Cache-TTL
  workspace?: string
  disabled_skills?: string[]
  require_tool_confirm?: boolean
  longterm_memory?: boolean
  // Memory-Injection-Settings (#115/#113). Alle optional, Backend backfillt.
  memory_max_crystals?: number
  memory_max_lessons?: number
  memory_min_lesson_confidence?: number
  memory_max_chars?: number
  memory_crystal_scope?: "project_and_global" | "project_only"
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
  tool_result_max_chars?: number
}
