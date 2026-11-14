import { api } from "@/shared/api-client"
import type { AgentTemplate, BoundAgent, ChainTestResult, TemplateBody, TemplateDetail, TemplateHealth } from "./types"

export const templatesApi = {
  list: () => api.get<{ templates: AgentTemplate[]; groups: string[] }>("/agent-templates"),
  get: (id: string) => api.get<TemplateDetail>(`/agent-templates/${encodeURIComponent(id)}`),
  save: (id: string, body: TemplateBody) =>
    api.put<AgentTemplate & { affected: BoundAgent[] }>(`/agent-templates/${encodeURIComponent(id)}`, body),
  preview: (id: string, body: TemplateBody) =>
    api.post<{ changed: string[]; affected: BoundAgent[]; health: TemplateHealth }>(
      `/agent-templates/${encodeURIComponent(id)}/preview`, body),
  test: (id: string) =>
    api.post<{ template: string; results: ChainTestResult[] }>(`/agent-templates/${encodeURIComponent(id)}/test`, {}),
  revert: (id: string, revision: number) =>
    api.post<AgentTemplate>(`/agent-templates/${encodeURIComponent(id)}/revert/${revision}`, {}),
  remove: (id: string) => api.delete<{ deleted: string }>(`/agent-templates/${encodeURIComponent(id)}`),
}
