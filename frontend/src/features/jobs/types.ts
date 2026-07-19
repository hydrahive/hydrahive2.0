export type JobResourceKind = "container" | "vm" | "node"

export type JobStatus =
  | "queued"
  | "leased"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "expired"

export interface ComputeJob {
  job_id: string
  node_id: string
  resource_kind: JobResourceKind
  resource_id: string | null
  operation: string
  generation: number
  status: JobStatus
  attempts: number
  progress: number
  error_code: string | null
  created_by: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  lease_until: string | null
}

export interface ComputeJobEvent {
  event_id: number
  sequence: number
  event_type: string
  data: {
    progress?: number
    error_code?: string
    reason?: string
    [key: string]: unknown
  }
  created_at: string
}

export interface JobFilter {
  node_id?: string
  status?: JobStatus
  limit?: number
}

/** Job states that are still in flight (not terminal). */
export const ACTIVE_JOB_STATUSES: readonly JobStatus[] = ["queued", "leased", "running"]

/** Server permits cancellation only for non-terminal states. */
export function isCancellable(status: JobStatus): boolean {
  return status === "queued" || status === "leased" || status === "running"
}

export function isTerminal(status: JobStatus): boolean {
  return status === "succeeded" || status === "failed" || status === "cancelled" || status === "expired"
}
