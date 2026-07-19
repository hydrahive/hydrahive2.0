import { api } from "@/shared/api-client"
import type {
  ApprovalInput,
  ComputeNode,
  CreatedEnrollment,
  EnrollmentCreateInput,
} from "./types"

export const nodesApi = {
  list: () => api.get<ComputeNode[]>("/compute/nodes"),
  get: (id: string) => api.get<ComputeNode>(`/compute/nodes/${id}`),
  createEnrollment: (input: EnrollmentCreateInput) =>
    api.post<CreatedEnrollment>("/compute/enrollments", input),
  approve: (id: string, input: ApprovalInput) =>
    api.post<ComputeNode>(`/compute/nodes/${id}/approve`, input),
  drain: (id: string) => api.post<ComputeNode>(`/compute/nodes/${id}/drain`, {}),
  disable: (id: string) => api.post<ComputeNode>(`/compute/nodes/${id}/disable`, {}),
  enable: (id: string) => api.post<ComputeNode>(`/compute/nodes/${id}/enable`, {}),
  revoke: (id: string) => api.delete<ComputeNode>(`/compute/nodes/${id}`),
}
