import { api } from "@/shared/api-client"
import type { Project, ProjectCreate, ProjectGitRepo, ProjectServer, ProjectStats, ProjectSession, ServerKind } from "./types"

export const projectsApi = {
  list: () => api.get<Project[]>("/projects"),
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  create: (req: ProjectCreate) => api.post<Project>("/projects", req),
  update: (id: string, fields: Partial<ProjectCreate & { status: string; notes: string; tags: string[]; mcp_server_ids: string[]; allowed_plugins: string[]; allowed_specialists: string[]; llm_api_key: string }>) =>
    api.patch<Project>(`/projects/${id}`, fields),
  listFiles: (id: string, path = "") =>
    api.get<{ path: string; entries: { name: string; type: "file" | "dir"; size: number | null; modified: number }[] }>(`/projects/${id}/files?path=${encodeURIComponent(path)}`),
  readFile: (id: string, path: string) =>
    fetch(`/api/projects/${id}/files/read?path=${encodeURIComponent(path)}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("hh_token") ?? ""}` }
    }).then(r => r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))),
  delete: (id: string) => api.delete<void>(`/projects/${id}`),
  addMember: (id: string, username: string) =>
    api.post<Project>(`/projects/${id}/members/${username}`, {}),
  removeMember: (id: string, username: string) =>
    api.delete<Project>(`/projects/${id}/members/${username}`),
  getAgent: (id: string) => api.get<{ id: string; name: string; llm_model: string }>(`/projects/${id}/agent`),
  getSessions: (id: string) => api.get<ProjectSession[]>(`/projects/${id}/sessions`),
  getStats: (id: string) => api.get<ProjectStats>(`/projects/${id}/stats`),
  getRepos: (id: string) => api.get<ProjectGitRepo[]>(`/projects/${id}/git/repos`),
  cloneRepo: (id: string, body: { name: string; url: string; branch?: string; token?: string }) =>
    api.post<{ ok: boolean }>(`/projects/${id}/git/repos/clone`, body),
  initRepo: (id: string, name: string) =>
    api.post<{ ok: boolean }>(`/projects/${id}/git/repos/init`, { name }),
  putRepoConfig: (id: string, name: string, body: { remote_url?: string; git_token?: string }) =>
    api.put<{ ok: boolean }>(`/projects/${id}/git/repos/${encodeURIComponent(name)}/config`, body),
  commitRepo: (id: string, name: string, message: string) =>
    api.post<{ ok: boolean }>(`/projects/${id}/git/repos/${encodeURIComponent(name)}/commit`, { message }),
  pushRepo: (id: string, name: string) =>
    api.post<{ ok: boolean }>(`/projects/${id}/git/repos/${encodeURIComponent(name)}/push`, {}),
  pullRepo: (id: string, name: string) =>
    api.post<{ ok: boolean }>(`/projects/${id}/git/repos/${encodeURIComponent(name)}/pull`, {}),
  deleteRepo: (id: string, name: string) =>
    api.delete<void>(`/projects/${id}/git/repos/${encodeURIComponent(name)}`),
  getServers: (id: string) => api.get<ProjectServer[]>(`/projects/${id}/servers`),
  getAvailableServers: (id: string) =>
    api.get<ProjectServer[]>(`/projects/${id}/servers/available`),
  assignServer: (id: string, kind: ServerKind, serverId: string) =>
    api.post<{ ok: boolean }>(`/projects/${id}/servers/assign`, { kind, id: serverId }),
  unassignServer: (id: string, kind: ServerKind, serverId: string) =>
    api.delete<void>(`/projects/${id}/servers/${kind}/${encodeURIComponent(serverId)}`),
  getSamba: (id: string) =>
    api.get<{ enabled: boolean; share_name: string; user: string; password: string }>(`/projects/${id}/samba`),
  putSamba: (id: string, enabled: boolean) =>
    api.put<{ ok: boolean; enabled: boolean }>(`/projects/${id}/samba`, { enabled }),
}

export const usersApi = {
  list: () => api.get<{ username: string; role: string }[]>("/users"),
}
