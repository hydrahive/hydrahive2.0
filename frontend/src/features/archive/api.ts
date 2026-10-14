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

/** Externer Server (Etappe 3): Einstellungen ohne Passwort + Stand der Kopier-Reihe. */
export interface ArchiveRemote {
  host: string
  share: string
  subdir: string
  user: string
  configured: boolean
  password_set: boolean
  tested: boolean
  active: boolean
  waiting: number
  last_error: string | null
  next_try_in_s: number | null
  on_server: number
  local_only: number
  /** Etappe 3b: Pakete, deren lokale Kopie gelöscht ist. */
  remote_only: number
  /** Pakete, deren lokale Kopie gelöscht werden darf (geprüft auf dem Server, nicht von Hand abgelegt). */
  droppable: number
  droppable_bytes: number
}

export interface RemoteForm {
  host: string
  share: string
  subdir: string
  user: string
  /** Leer = altes Passwort behalten. */
  password: string
}

export type RemoteTestResult = { ok: true; free_bytes: number } | { ok: false; error: string }

export interface ArchiveStatus {
  target: "local"
  storage: ArchiveStorage
  share: ArchiveShare
  move?: ArchiveMove
  /** Lösch-Aufträge („Laufende Vorgänge“, Etappe 2). */
  jobs?: DeleteJobs
  remote?: ArchiveRemote
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
  remote?: { state?: string; verified_at?: string }
  /** false = lokale Kopie gelöscht, liegt nur noch auf dem Server (Etappe 3b). */
  local?: boolean
}

/** Stand der Kopie auf dem Server je Paket (Etappe 3, 3b). */
export function remoteStateOf(e: { remote?: { state?: string } }): "server" | "server_only" | "waiting" | "local" {
  if (e.remote?.state === "verified") return "server"
  if (e.remote?.state === "remote_only") return "server_only"
  if (e.remote?.state === "pending") return "waiting"
  return "local"
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
  remoteSave: (form: RemoteForm) => api.put<ArchiveRemote>("/admin/archive/remote", form),
  remoteTest: () => api.post<RemoteTestResult>("/admin/archive/remote/test", {}),
  remoteActive: (active: boolean) => api.post<ArchiveRemote>("/admin/archive/remote/active", { active }),
  remoteSync: () => api.post<{ queued: number }>("/admin/archive/remote/sync", {}),
  dropLocal: (sel: { paths: string[] } | { all_verified: true }) =>
    api.post<{ job_id: string; count: number }>("/admin/archive/entries/drop-local", sel),
  setShare: (enabled: boolean) =>
    api.put<{ folder: boolean; share: string; error?: string }>("/admin/archive/share", { enabled }),
}
