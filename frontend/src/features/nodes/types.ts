export type NodeKind = "local" | "agent"

export type NodeStatus =
  | "pending"
  | "online"
  | "degraded"
  | "offline"
  | "draining"
  | "disabled"
  | "revoked"

export interface ComputeNode {
  node_id: string
  name: string
  kind: NodeKind
  status: NodeStatus
  protocol_version: number
  created_at: string
  updated_at: string
  last_sequence: number
  capabilities: Record<string, unknown>
  resources: Record<string, unknown>
  labels: Record<string, unknown>
  health_errors: string[]
  certificate_fingerprint: string | null
  agent_version: string | null
  last_seen_at: string | null
  approved_at: string | null
  approved_by: string | null
  revoked_at: string | null
}

export interface EnrollmentCreateInput {
  requested_name: string
  ttl_seconds?: number
}

/** Response of POST /compute/enrollments — the plaintext token is shown exactly once. */
export interface CreatedEnrollment {
  token_id: string
  token: string
  requested_name: string
  expires_at: string
}

export interface ApprovalInput {
  certificate_fingerprint: string
}

/** Normalized resource inventory a node reports; all fields optional/best-effort. */
export interface NodeResources {
  cpu_cores?: number
  memory_mb?: number
  storage_gb?: number
  [key: string]: unknown
}

/** Normalized capability flags a node reports. */
export interface NodeCapabilities {
  incus?: boolean
  kvm?: boolean
  [key: string]: unknown
}
