import { api } from "@/shared/api-client"

export interface HarnessFinding {
  rule_id: string; title: string; actual: unknown; target: string; deduction: number
  severity: "critical" | "warning" | "info"; source: string; recommendation: string
}
export interface HarnessDimension { id: string; label: string; score: number; findings: HarnessFinding[] }
export interface HarnessAgentOutlier {
  id: string; name: string; type: string; project_id?: string | null
  configured_tools: number; tool_schemas: number; tool_schema_chars: number
  skills: number; skill_metadata_chars: number; system_prompt_chars: number
  execution_mode: string; collection_error?: boolean
}
export interface HarnessDoctorResult {
  generated_at: string; window_hours: number; overall_score: number; lowest_dimension: string
  dimensions: HarnessDimension[]; priorities: HarnessFinding[]; agent_outliers: HarnessAgentOutlier[]
  snapshot: Record<string, unknown>; notes: string[]
}
export const harnessDoctorApi = {
  read: (hours: number) => api.get<HarnessDoctorResult>(`/system/harness-doctor?hours=${hours}`),
}
