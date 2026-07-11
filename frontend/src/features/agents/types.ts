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
  reasoning_effort?: string
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
  compact_max_turns?: number | null  // null = window-skalierter Default (Turn-Netz)
  tool_result_max_chars?: number  // 0 = kein Limit; live-truncation vor LLM-Call
  cache_ttl?: string              // "5m" | "1h" — Anthropic Prompt-Cache-TTL
  max_iterations?: number
  workspace?: string
  disabled_skills?: string[]
  require_tool_confirm?: boolean
  longterm_memory?: boolean
  // Per-Agent Postfach (Schicht 2). Leer = globale Mail-Settings. Passwort wird
  // von der API maskiert ausgeliefert ("" + password_set); leeres Passwort beim
  // Speichern = bestehendes behalten.
  tool_config?: AgentToolConfig
}

export interface MailAccountConfig {
  host?: string
  port?: number
  user?: string
  password?: string
  password_set?: boolean   // read-only von der API: ob ein Passwort gespeichert ist
  from?: string            // nur SMTP
  use_tls?: boolean        // nur SMTP
}

export interface AgentToolConfig {
  smtp?: MailAccountConfig
  imap?: MailAccountConfig
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

export interface AgentTemplate {
  id: string
  type: string
  name: string
  description: string
  llm_model: string
  tools: string[]
  temperature: number
  max_tokens: number
  thinking_budget: number
  system_prompt: string
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
  reasoning_effort?: string
  mcp_servers: string[]
  fallback_models: string[]
  owner?: string | null
  domain?: string | null
  system_prompt?: string | null
  compact_model?: string
  compact_tool_result_limit?: number
  compact_reserve_tokens?: number
  compact_threshold_pct?: number
  compact_max_turns?: number | null
  tool_result_max_chars?: number
  max_iterations?: number
}
