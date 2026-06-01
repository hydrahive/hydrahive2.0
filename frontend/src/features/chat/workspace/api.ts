import { api } from "@/shared/api-client"

export interface TreeEntry { name: string; is_dir: boolean; size: number | null }
export interface FileContent { path: string; content: string }

export const workspaceApi = {
  tree: (agentId: string, path = "") =>
    api.get<TreeEntry[]>(`/workspace/tree?agent_id=${agentId}&path=${encodeURIComponent(path)}`),
  file: (agentId: string, path: string) =>
    api.get<FileContent>(`/workspace/file?agent_id=${agentId}&path=${encodeURIComponent(path)}`),
  save: (agentId: string, path: string, content: string) =>
    api.put<{ ok: boolean }>(`/workspace/file`, { agent_id: agentId, path, content }),
}
