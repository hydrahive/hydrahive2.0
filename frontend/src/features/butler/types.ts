import type { Edge, Node } from "@xyflow/react"

// Frontend-Shape — was die alte octopos-ButlerPage.tsx erwartet:
// nodes als ReactFlow-Node mit data.{subtype,label,params}, edges mit sourceHandle.
export interface ButlerNodeData {
  subtype: string
  label: string
  params: Record<string, unknown>
  [key: string]: unknown  // React Flow benötigt eine Index-Signatur
}

export interface ButlerFlow {
  id: string
  name: string
  enabled: boolean
  scope_id: string | null
  nodes: Node<ButlerNodeData>[]
  edges: Edge[]
}

export type BNode = Node<ButlerNodeData>

// Backend-Shape — was unser FastAPI liefert (flach, snake_case).
export type BackendNode = {
  id: string
  type: "trigger" | "condition" | "action"
  subtype: string
  position: { x: number; y: number }
  params: Record<string, unknown>
  label: string | null
}

export type BackendEdge = {
  id: string
  source: string
  target: string
  source_handle: "output" | "true" | "false"
}

export type BackendFlow = {
  flow_id: string
  owner: string
  name: string
  enabled: boolean
  scope: "user" | "project"
  scope_id: string | null
  nodes: BackendNode[]
  edges: BackendEdge[]
}
