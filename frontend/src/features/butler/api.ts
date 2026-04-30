import { api } from "@/shared/api-client"
import type { DryRunResult, Flow, RegistryMeta } from "./types"

export interface FlowSaveInput {
  flow_id: string
  name: string
  enabled: boolean
  nodes: Flow["nodes"]
  edges: Flow["edges"]
  scope?: "user" | "project"
  scope_id?: string | null
}

export const butlerApi = {
  registry: () => api.get<RegistryMeta>("/butler/registry"),
  list: () => api.get<Flow[]>("/butler/flows"),
  get: (id: string) => api.get<Flow>(`/butler/flows/${id}`),
  create: (input: FlowSaveInput) => api.post<Flow>("/butler/flows", input),
  update: (id: string, input: FlowSaveInput) =>
    api.put<Flow>(`/butler/flows/${id}`, input),
  remove: (id: string) => api.delete<void>(`/butler/flows/${id}`),
  dryRun: (id: string, event: Record<string, unknown>) =>
    api.post<DryRunResult>(`/butler/flows/${id}/dry_run`, { event }),
}
