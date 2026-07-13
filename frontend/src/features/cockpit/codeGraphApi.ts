import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"

export interface CodeGraphGodNode { name: string; edges: number }
export interface CodeGraphReport { god_nodes?: CodeGraphGodNode[]; cycles?: string[] }

export interface CodeGraphStatus {
  installed: boolean
  built_at: string | null
  scan_dirs: string[]
  metrics: { nodes?: number; edges?: number; communities?: number }
  report: CodeGraphReport
  html_path: string | null
  report_path: string | null
}

export interface CodeGraphConfig {
  scan_dirs: string[]
  updated_at: string | null
  suggestions: string[]
}

export interface CodeGraphDirEntry { rel: string; name: string; has_children: boolean }
export interface CodeGraphBrowse {
  path: string
  parent: string | null
  dirs: CodeGraphDirEntry[]
}

export interface CodeGraphBuildResult {
  built_at: string
  scan_dirs: string[]
  metrics: { nodes?: number; edges?: number; communities?: number }
  report: CodeGraphReport
  html_path: string | null
  report_path: string | null
}

const base = (projectId: string) => `/projects/${projectId}/code-graph`

export const codeGraphApi = {
  status: (projectId: string) => api.get<CodeGraphStatus>(`${base(projectId)}/status`),
  getConfig: (projectId: string) => api.get<CodeGraphConfig>(`${base(projectId)}/config`),
  browse: (projectId: string, path = "") => api.get<CodeGraphBrowse>(`${base(projectId)}/config/browse?path=${encodeURIComponent(path)}`),
  setConfig: (projectId: string, scanDirs: string[]) => api.put<CodeGraphConfig>(`${base(projectId)}/config`, { scan_dirs: scanDirs }),
  build: (projectId: string) => api.post<CodeGraphBuildResult>(`${base(projectId)}/build`, {}),
}

/** Absoluten Datei-Pfad über /api/files laden (mit Token-Query, da iframe/img
 *  keinen Authorization-Header schicken können). */
export function graphFileUrl(absPath: string): string {
  const token = useAuthStore.getState().token
  const tokenParam = token ? `&token=${encodeURIComponent(token)}` : ""
  return `/api/files?path=${encodeURIComponent(absPath)}${tokenParam}`
}
