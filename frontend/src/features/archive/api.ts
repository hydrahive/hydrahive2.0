import { api } from "@/shared/api-client"
import type { DeleteJobs } from "./delete/api"

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
  /** Standard-Ort bei den Projektdaten (workspaces/archive). */
  is_default: boolean
  /** Einhängepunkt der Platte, auf der das Archiv liegt. */
  mount: string
  /** Grund, falls HydraHive Ordner oder Freigabe nicht einrichten konnte. */
  setup_error: string
}

export interface ArchiveShare {
  name: string
  /** Während eines Umzugs ruht die Freigabe. */
  paused_for_move?: boolean
  /** Schalter in der Admin-Konsole. */
  wanted: boolean
  /** Freigabe-Datei ist tatsächlich angelegt. */
  enabled: boolean
  samba_installed: boolean
  samba_running: boolean
  login: string
  password: string
}

export type MoveProblem =
  | "move_running" | "same_location" | "target_inside_current" | "current_inside_target"
  | "target_not_empty" | "target_not_writable" | "not_enough_space"

export interface ArchiveLocation {
  /** "default" oder 12-stellige ID einer Platte – nie ein Pfad. */
  id: string
  kind: "default" | "disk"
  path: string
  mount: string
  device: string
  fstype: string
  size_bytes: number
  free_bytes: number
  writable: boolean
  current: boolean
  problems: MoveProblem[]
}

export interface MoveRunning {
  state: "starting" | "copying" | "verifying" | "cleanup"
  copied_bytes: number
  total_bytes: number
  total_files?: number
  target: string
}

export interface MoveResult {
  state: "done" | "failed"
  target?: string
  left_behind?: string[]
  error?: string
  detail?: string
}

export interface ArchiveMove {
  running: MoveRunning | null
  last: MoveResult | null
}

export interface ArchiveStatus {
  target: "local"
  storage: ArchiveStorage
  share: ArchiveShare
  move?: ArchiveMove
  /** Lösch-Aufträge („Laufende Vorgänge“, Etappe 2). */
  jobs?: DeleteJobs
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

/** Waisen (Etappe 2b): Arbeitsordner ohne Agent und Agenten ohne Projekt. */
export interface OrphanWorkspace {
  id: string
  kind: "specialists" | "master"
  size: number
  files: number
  /** Keine Dateien oder nur die unveränderte startup.md. */
  empty: boolean
  complete: boolean
}

export interface OrphanAgent {
  id: string
  name: string
  project_id: string
  type?: string
}

export interface OrphanScan {
  workspaces: OrphanWorkspace[]
  agents: OrphanAgent[]
  complete: boolean
}

/** Genau die angezeigten IDs – was erst danach verwaist, bleibt unberührt (Spec archiv-system.md, 2b). */
export function cleanupSelection(scan: OrphanScan): { workspaces: string[]; agents: string[] } {
  return { workspaces: scan.workspaces.map((w) => w.id), agents: scan.agents.map((a) => a.id) }
}

export const archiveApi = {
  status: () => api.get<ArchiveStatus>("/admin/archive/status"),
  entries: (kind: ArchiveKind | null) =>
    api.get<{ entries: ArchiveEntry[] }>(kind ? `/admin/archive/entries?kind=${kind}` : "/admin/archive/entries"),
  emptyTrash: (confirm: string) => api.post<{ freed_bytes: number }>("/admin/archive/trash/empty", { confirm }),
  locations: () => api.get<{ entries: ArchiveLocation[] }>("/admin/archive/locations"),
  move: (location: string) => api.post<{ started: boolean; target: string }>("/admin/archive/move", { location }),
  prepare: (location: string) => api.post<{ started: boolean }>(`/admin/archive/locations/${location}/prepare`, {}),
  orphans: () => api.get<OrphanScan>("/admin/archive/orphans"),
  cleanupOrphans: (sel: { workspaces: string[]; agents: string[] }) =>
    api.post<{ job_ids: string[] }>("/admin/archive/orphans/cleanup", sel),
  setShare: (enabled: boolean) =>
    api.put<{ folder: boolean; share: string; error?: string }>("/admin/archive/share", { enabled }),
}
