// Katalog-Reiter auf Clients (docs/specs/federation-shared-tasks.md §Oberfläche Cockpit):
// reine Hilfsfunktionen für Filter und Abfrage der Kopie. Ohne React, direkt testbar.
import { toggleIn } from "./_catalogSync"
import type { CatalogMirrorQuery } from "./api"

export const STATUS_OPTIONS: Record<"task" | "idea", readonly string[]> = {
  task: ["open", "in_progress", "done", "cancelled"],
  idea: ["new", "review", "planned", "parked", "done", "dropped"],
}

export const KINDS = ["task", "idea"] as const
export type MirrorKind = (typeof KINDS)[number]

export const MIRROR_LIMIT = 50

/** Bedienstand der Filter im Katalog-Reiter. ``kind=null`` = beide Arten. */
export interface MirrorFilters {
  instances: string[]
  project: string | null
  statuses: string[]
  kind: MirrorKind | null
  q: string
}

export const EMPTY_FILTERS: MirrorFilters = { instances: [], project: null, statuses: [], kind: null, q: "" }

export function toggleInstance(f: MirrorFilters, fp: string): MirrorFilters {
  return { ...f, instances: toggleIn(f.instances, fp) }
}

export function toggleStatus(f: MirrorFilters, status: string): MirrorFilters {
  return { ...f, statuses: toggleIn(f.statuses, status) }
}

/** Beim Wechsel der Art passen nur noch Status-Werte dieser Art — sonst würde ein Status
 * der anderen Art unsichtbar weiterfiltern. */
export function setKind(f: MirrorFilters, kind: MirrorKind | null): MirrorFilters {
  if (!kind) return { ...f, kind: null }
  const valid = new Set(STATUS_OPTIONS[kind])
  return { ...f, kind, statuses: f.statuses.filter(s => valid.has(s)) }
}

/** Query für ``catalogApi.getMirror``. ``offset=0`` bei jeder Filteränderung (neue Seite 1). */
export function toMirrorQuery(f: MirrorFilters, offset = 0): CatalogMirrorQuery {
  return {
    instance: f.instances.length ? f.instances : undefined,
    project: f.project ?? undefined,
    status: f.statuses.length ? f.statuses : undefined,
    kind: f.kind ?? undefined,
    q: f.q.trim() || undefined,
    limit: MIRROR_LIMIT,
    offset,
  }
}

export function formatDate(iso: string | null | undefined, never: string): string {
  return iso ? new Date(iso).toLocaleString() : never
}
