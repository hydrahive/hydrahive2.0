import { api } from "@/shared/api-client"
import type { Project, ProjectCreate } from "./types"

export const projectsApi = {
  list: () => api.get<Project[]>("/projects"),
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  create: (req: ProjectCreate) => api.post<Project>("/projects", req),
  update: (id: string, fields: Partial<ProjectCreate & { status: string }>) =>
    api.patch<Project>(`/projects/${id}`, fields),
  delete: (id: string) => api.delete<void>(`/projects/${id}`),
  addMember: (id: string, username: string) =>
    api.post<Project>(`/projects/${id}/members/${username}`, {}),
  removeMember: (id: string, username: string) =>
    api.delete<Project>(`/projects/${id}/members/${username}`),
  getAgent: (id: string) => api.get<{ id: string; name: string; llm_model: string }>(`/projects/${id}/agent`),
}

export const usersApi = {
  list: () => api.get<{ username: string; role: string }[]>("/users"),
}
