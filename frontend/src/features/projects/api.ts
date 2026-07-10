import { api } from "@/shared/api-client"
import type { Project, ProjectAuditEntry, ProjectCreate, ProjectGiteaStatus, ProjectGitRepo, ProjectServer, ProjectStats, ProjectSession, ServerKind, SmbMount, SmbMountCreate } from "./types"

export const projectsApi = {
  list: () => api.get<Project[]>("/projects"),
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  create: (req: ProjectCreate) => api.post<Project>("/projects", req),
  update: (id: string, fields: Partial<ProjectCreate & { status: string; notes: string; tags: string[]; mcp_server_ids: string[]; allowed_plugins: string[]; allowed_specialists: string[]; llm_api_key: string }>) =>
    api.patch<Project>(`/projects/${id}`, fields),
  listFiles: (id: string, path = "") =>
    api.get<{ path: string; entries: { name: string; type: "file" | "dir"; size: number | null; modified: number }[] }>(`/projects/${id}/files?path=${encodeURIComponent(path)}`),
  readFile: async (id: string, path: string) => {
    const { useAuthStore } = await import("@/features/auth/useAuthStore")
    const token = useAuthStore.getState().token
    const res = await fetch(`/api/projects/${id}/files/read?path=${encodeURIComponent(path)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.text()
  },
  writeFile: (id: string, path: string, content: string) =>
    api.post<{ ok: boolean; size: number }>(`/projects/${id}/files/write`, { path, content }),
  uploadFile: (id: string, file: File, path = "") => {
    const form = new FormData()
    form.append("file", file)
    const qs = path ? `?path=${encodeURIComponent(path)}` : ""
    return api.postForm<{ ok: boolean; name: string; size: number }>(`/projects/${id}/files/upload${qs}`, form)
  },
  deleteFile: (id: string, path: string) =>
    api.delete<{ ok: boolean }>(`/projects/${id}/files?path=${encodeURIComponent(path)}`),
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
  getGiteaStatus: (id: string, name: string) =>
    api.get<ProjectGiteaStatus>(`/projects/${id}/git/repos/${encodeURIComponent(name)}/gitea`),
  createGiteaRepo: (id: string, name: string) =>
    api.post<{ ok: boolean; status: ProjectGiteaStatus }>(`/projects/${id}/git/repos/${encodeURIComponent(name)}/gitea/create`, {}),
  pushGiteaRepo: (id: string, name: string) =>
    api.post<{ ok: boolean }>(`/projects/${id}/git/repos/${encodeURIComponent(name)}/gitea/push`, {}),
  pullGiteaRepo: (id: string, name: string) =>
    api.post<{ ok: boolean }>(`/projects/${id}/git/repos/${encodeURIComponent(name)}/gitea/pull`, {}),
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
  // SMB-Mounts: CRUD (user-scoped) + Projekt-Zuweisung
  listMounts: () => api.get<SmbMount[]>("/smb-mounts"),
  createMount: (body: SmbMountCreate) => api.post<SmbMount>("/smb-mounts", body),
  deleteMount: (mountId: string) => api.delete<void>(`/smb-mounts/${mountId}`),
  getProjectMounts: (id: string) =>
    api.get<SmbMount[]>(`/projects/${id}/mounts`),
  getAvailableMounts: (id: string) =>
    api.get<SmbMount[]>(`/projects/${id}/mounts/available`),
  assignMount: (id: string, mountId: string) =>
    api.post<SmbMount>(`/projects/${id}/mounts/assign`, { id: mountId }),
  unassignMount: (id: string, mountId: string) =>
    api.delete<void>(`/projects/${id}/mounts/${encodeURIComponent(mountId)}`),
  getAudit: (id: string, params?: { action?: string; user?: string; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.action) qs.set("action", params.action)
    if (params?.user) qs.set("user", params.user)
    if (params?.limit != null) qs.set("limit", String(params.limit))
    const query = qs.toString()
    return api.get<{ entries: ProjectAuditEntry[]; count: number }>(
      `/projects/${id}/audit${query ? `?${query}` : ""}`,
    )
  },
}

export const usersApi = {
  list: () => api.get<{ username: string; role: string }[]>("/users"),
}
