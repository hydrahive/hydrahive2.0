import { api } from "@/shared/api-client"

export type ArchiveKind = "agents" | "projects" | "users" | "backups" | "uploads"

export interface ArchiveStorage {
  path: string
  exists: boolean
  writable: boolean
  count: number
  manual_count: number
  by_kind: Partial<Record<ArchiveKind, number>>
  used_bytes: number
  free_bytes: number
  trash_bytes: number
}

export interface ArchiveShare {
  name: string
  enabled: boolean
  samba_installed: boolean
  samba_running: boolean
  login: string
  password: string
}

export interface ArchiveStatus {
  target: "local"
  storage: ArchiveStorage
  share: ArchiveShare
}

export interface ArchiveEntry {
  manual: boolean
  path: string
  file: string
  kind: ArchiveKind | string | null
  size: number
  mtime: number
  name?: string
  owner?: string | null
  reason?: string
  created_at?: string
  sha256?: string
  source_id?: string
}

export const archiveApi = {
  status: () => api.get<ArchiveStatus>("/admin/archive/status"),
  entries: (kind: ArchiveKind | null) =>
    api.get<{ entries: ArchiveEntry[] }>(kind ? `/admin/archive/entries?kind=${kind}` : "/admin/archive/entries"),
  emptyTrash: (confirm: string) => api.post<{ freed_bytes: number }>("/admin/archive/trash/empty", { confirm }),
}
