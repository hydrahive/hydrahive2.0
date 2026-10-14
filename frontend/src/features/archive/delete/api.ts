import { api } from "@/shared/api-client"

/** Lösch-Ziele (Spec archiv-system.md, Etappe 2). */
export type DeleteKind = "agent" | "project" | "user" | "instance"
export type DeleteMode = "archive" | "permanent"

export interface DeletePreview {
  kind: DeleteKind
  id: string
  name: string
  agents: { id: string; name: string }[]
  chats: number
  projects: { id: string; name: string }[]
  members: Record<string, { username: string; role: string }[]>
  mounts_skipped: string[]
  /** Agenten des Nutzers in fremden Projekten – gehen an den Projekt-Ersteller. */
  hand_over: number
  memberships: number
  /** Was beim Nutzer bestehen bleibt (VMs, Container, SMB-Verbindungen). */
  stays: Partial<Record<"vms" | "containers" | "smb_mounts", number>>
  size: { bytes: number; complete: boolean }
  archive: { path: string; share: string | null; free_bytes: number; possible: boolean; reason: string | null }
}

export type DeleteStep = "queued" | "lock" | "measure" | "pack" | "delete" | "done"

export interface DeleteJob {
  id: string
  /** Auch Waisen-Aufträge (Etappe 2b) laufen in derselben Reihe. */
  kind: DeleteKind | "orphans" | "orphan_agent"
  target: string
  name: string
  mode: DeleteMode
  state: "queued" | "running" | "done" | "failed"
  step: DeleteStep
  error: string | null
  bytes_total: number
  bytes_done: number
  files_total: number
  packages: { kind: string; file: string }[]
  package?: string
  leftovers: string[]
}

export interface DeleteJobs {
  running: DeleteJob | null
  queued: DeleteJob[]
  done: DeleteJob[]
}

const ROUTE: Record<DeleteKind, (id: string) => string> = {
  agent: (id) => `/agents/${encodeURIComponent(id)}`,
  project: (id) => `/projects/${encodeURIComponent(id)}`,
  user: (id) => `/users/${encodeURIComponent(id)}`,
  instance: (id) => `/external-instances/${encodeURIComponent(id)}`,
}

export const deleteApi = {
  preview: (kind: DeleteKind, id: string) =>
    api.get<DeletePreview>(`/admin/archive/delete-preview?kind=${kind}&id=${encodeURIComponent(id)}`),
  start: (kind: DeleteKind, id: string, mode: DeleteMode, confirm: string) => {
    const query = new URLSearchParams({ mode })
    if (mode === "permanent") query.set("confirm", confirm)
    return api.delete<{ job_id: string }>(`${ROUTE[kind](id)}?${query.toString()}`)
  },
  jobs: () => api.get<DeleteJobs>("/admin/archive/jobs"),
}

/** Vorauswahl im Dialog: „Ins Archiv“, wenn möglich – „Unwiderruflich“ nie (Spec archiv-system.md). */
export function initialMode(preview: DeletePreview): DeleteMode | null {
  return preview.archive.possible ? "archive" : null
}

/** Auftrag nach ID in der Liste suchen (laufend, wartend oder fertig). */
export function findJob(jobs: DeleteJobs, id: string): DeleteJob | null {
  if (jobs.running?.id === id) return jobs.running
  return jobs.queued.find((j) => j.id === id) ?? jobs.done.find((j) => j.id === id) ?? null
}
