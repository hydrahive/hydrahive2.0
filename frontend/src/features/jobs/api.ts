import { api } from "@/shared/api-client"
import type { ComputeJob, ComputeJobEvent, JobFilter } from "./types"

function buildQuery(filter: JobFilter): string {
  const params = new URLSearchParams()
  if (filter.node_id) params.set("node_id", filter.node_id)
  if (filter.status) params.set("status", filter.status)
  if (filter.limit) params.set("limit", String(filter.limit))
  const query = params.toString()
  return query ? `?${query}` : ""
}

export const jobsApi = {
  list: (filter: JobFilter = {}) => api.get<ComputeJob[]>(`/compute/jobs${buildQuery(filter)}`),
  get: (id: string) => api.get<ComputeJob>(`/compute/jobs/${id}`),
  events: (id: string) => api.get<ComputeJobEvent[]>(`/compute/jobs/${id}/events`),
  cancel: (id: string) => api.post<ComputeJob>(`/compute/jobs/${id}/cancel`, {}),
}
