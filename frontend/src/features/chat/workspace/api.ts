import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"

export interface TreeEntry { name: string; is_dir: boolean; size: number | null }
export interface FileContent { path: string; content: string }

export const workspaceApi = {
  tree: (agentId: string, path = "") =>
    api.get<TreeEntry[]>(`/workspace/tree?agent_id=${agentId}&path=${encodeURIComponent(path)}`),
  file: (agentId: string, path: string) =>
    api.get<FileContent>(`/workspace/file?agent_id=${agentId}&path=${encodeURIComponent(path)}`),
  save: (agentId: string, path: string, content: string) =>
    api.put<{ ok: boolean }>(`/workspace/file`, { agent_id: agentId, path, content }),

  /** Rohe Bytes als Object-URL holen (mit Auth-Header) — für Viewer + Download.
   *  Caller ist für URL.revokeObjectURL() verantwortlich. */
  async rawObjectUrl(agentId: string, path: string): Promise<string> {
    const token = useAuthStore.getState().token
    const res = await fetch(
      `/api/workspace/raw?agent_id=${agentId}&path=${encodeURIComponent(path)}`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} },
    )
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  },
}

export interface GitRepo { name: string; branch: string | null }
export interface GitFile { status: string; path: string; staged: boolean }
export interface GitStatus { is_repo: boolean; branch: string | null; files: GitFile[] }

export const gitApi = {
  repos: (agentId: string) =>
    api.get<GitRepo[]>(`/workspace/git/repos?agent_id=${agentId}`),
  status: (agentId: string, repo: string) =>
    api.get<GitStatus>(`/workspace/git/status?agent_id=${agentId}&repo=${encodeURIComponent(repo)}`),
  diff: (agentId: string, repo: string, file: string) =>
    api.get<{ diff: string }>(`/workspace/git/diff?agent_id=${agentId}&repo=${encodeURIComponent(repo)}&file=${encodeURIComponent(file)}`),
  stage: (agentId: string, repo: string, file: string, staged: boolean) =>
    api.post<{ ok: boolean }>(`/workspace/git/stage`, { agent_id: agentId, repo, file, staged }),
  commit: (agentId: string, repo: string, message: string) =>
    api.post<{ sha: string }>(`/workspace/git/commit`, { agent_id: agentId, repo, message }),
}
