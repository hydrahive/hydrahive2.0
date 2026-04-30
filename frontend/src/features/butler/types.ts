export type NodeType = "trigger" | "condition" | "action"
export type Scope = "user" | "project"
export type SourceHandle = "output" | "true" | "false"
export type ParamKind =
  | "text" | "textarea" | "select" | "time" | "number" | "checkbox" | "list_text"

export interface ParamSchema {
  key: string
  label: string
  kind: ParamKind
  required: boolean
  options: string[]
  placeholder: string | null
  default: unknown
}

export interface SpecMeta {
  subtype: string
  label: string
  description: string
  params: ParamSchema[]
}

export interface RegistryMeta {
  triggers: SpecMeta[]
  conditions: SpecMeta[]
  actions: SpecMeta[]
}

export interface NodePosition {
  x: number
  y: number
}

export interface ButlerNode {
  id: string
  type: NodeType
  subtype: string
  position: NodePosition
  params: Record<string, unknown>
  label: string | null
}

export interface ButlerEdge {
  id: string
  source: string
  target: string
  source_handle: SourceHandle
}

export interface Flow {
  flow_id: string
  name: string
  owner: string
  enabled: boolean
  scope: Scope
  scope_id: string | null
  nodes: ButlerNode[]
  edges: ButlerEdge[]
  created_at: string | null
  modified_at: string | null
  modified_by: string | null
}

export interface DryRunTraceEntry {
  node_id: string
  type?: NodeType
  subtype?: string
  label?: string | null
  decision?: string
  detail?: string | null
  ok?: boolean
}

export interface DryRunResult {
  matched: boolean
  trace: DryRunTraceEntry[]
  actions_executed: { node_id: string; subtype: string; ok: boolean; detail: string | null }[]
}
