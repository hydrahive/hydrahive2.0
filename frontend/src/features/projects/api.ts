import { api } from "@/shared/api-client"
import type { Project, ProjectCreate, ProjectGitStatus, ProjectStats, ProjectSession } from "./types"

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
  getSessions: (id: string) => api.get<ProjectSession[]>(`/projects/${id}/sessions`),
  getGit: (id: string) => api.get<ProjectGitStatus>(`/projects/${id}/git`),
  getStats: (id: string) => api.get<ProjectStats>(`/projects/${id}/stats`),
  putGitConfig: (id: string, body: { remote_url?: string; git_token?: string }) =>
    api.put<{ ok: boolean }>(`/projects/${id}/git/config`, body),
  gitInit: (id: string) => api.post<{ ok: boolean }>(`/projects/${id}/git/init`, {}),
  gitClone: (id: string, body: { url: string; branch?: string }) =>
    api.post<{ ok: boolean }>(`/projects/${id}/git/clone`, body),
  gitCommit: (id: string, message: string) =>
    api.post<{ ok: boolean }>(`/projects/${id}/git/commit`, { message }),
  gitPush: (id: string) => api.post<{ ok: boolean }>(`/projects/${id}/git/push`, {}),
  gitPull: (id: string) => api.post<{ ok: boolean }>(`/projects/${id}/git/pull`, {}),
}

export const usersApi = {
  list: () => api.get<{ username: string; role: string }[]>("/users"),
}
