/** Agenten-Templates (Spec docs/specs/agent-templates.md). Spiegelt die Antwort von /api/agent-templates. */
export type TemplateGroup = "personal" | "projects" | "specialists" | "modules" | "system"
export type HealthState = "green" | "yellow" | "red"

export interface TemplateBudget {
  max_iterations: number
  max_tokens: number
  timeout_seconds: number
  compact_threshold_pct: number
  overrun_pct: number
  cooldown_seconds: number
  reasoning_effort: string
  cache_ttl: "5m" | "1h"
}

export interface TemplateReply {
  summary_max_chars: number
  full_report: "file" | "inline"
}

export interface TemplateHealth {
  state: HealthState
  unknown_models: string[]
  same_provider: boolean
  primary_down: boolean
  providers: string[]
}

export interface AgentTemplate {
  id: string
  label: string
  group: TemplateGroup
  chain: string[]
  failover_on: string[]
  budget: TemplateBudget
  reply: TemplateReply
  on_demand: boolean
  description: string
  revision: number
  updated_at?: string
  updated_by?: string
  health?: TemplateHealth
  bound_count?: number
}

export interface BoundAgent {
  id: string
  name: string
  type: string
  owner: string
  managed_by: string | null
  llm_model: string
}

export interface TemplateDetail extends AgentTemplate {
  bound: BoundAgent[]
  history: { revision: number; updated_at?: string; updated_by?: string }[]
}

export interface ChainTestResult {
  model: string
  ok: boolean
  answer?: string
  reason?: string
  message?: string
}

export type TemplateBody = Pick<AgentTemplate,
  "label" | "group" | "chain" | "failover_on" | "budget" | "reply" | "on_demand" | "description">
