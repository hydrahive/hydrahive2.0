// Projekt-Zuordnung (docs/specs/federation-shared-tasks.md §Korrektur im Cockpit,
// §Projekte, die es nur auf einer Seite gibt): Typen, API und reine Logik.
import { api } from "@/shared/api-client"
import type { ProjectCreate } from "@/features/projects/types"

export type MapReason =
  | "manual" | "name" | "hidden" | "ambiguous" | "no_match" | "not_member" | "no_project" | "target_unavailable"

/** Eine Zeile aus GET /api/federation/catalog/project-map. */
export interface OriginProject {
  origin_fp: string
  origin_name: string | null
  origin_project_id: string
  project_name: string | null
  count: number
  /** "auto" | "hidden" | lokale project_id */
  setting: string
  local_project_id: string | null
  hidden: boolean
  reason: MapReason
}

export interface ProjectMapPut {
  origin_fp: string
  origin_project_id: string
  target: string
}

export const projectMapApi = {
  list: (): Promise<{ origins: OriginProject[] }> => api.get("/federation/catalog/project-map"),
  set: (body: ProjectMapPut): Promise<{ origins: OriginProject[] }> => api.put("/federation/catalog/project-map", body),
}

/** Gründe, die als Hinweis angezeigt werden (Zuordnung fehlt oder ist kaputt). */
const HINT_REASONS: ReadonlySet<MapReason> = new Set(["ambiguous", "no_match", "not_member", "target_unavailable"])

export function hintFor(o: OriginProject): MapReason | null {
  return HINT_REASONS.has(o.reason) ? o.reason : null
}

/** Nicht zugeordnet = kein lokales Projekt und nicht bewusst „nicht anzeigen“. */
export function isUnassigned(o: OriginProject): boolean {
  return o.local_project_id === null && !o.hidden
}

/** Knopf „Projekt hier anlegen“: nur bei „kein gleichnamiges Projekt“ und mit Namen. */
export function canCreateHere(o: OriginProject): boolean {
  return o.reason === "no_match" && newProjectName(o) !== ""
}

export function newProjectName(o: OriginProject): string {
  return (o.project_name ?? "").trim()
}

/** Nutzlast für das bestehende POST /api/projects: leeres Projekt, nur der Name vom Ursprung,
 *  Mitglied = angemeldeter Nutzer, sonst Standardwerte (Standard-Template, kein Git). */
export function createPayload(o: OriginProject, username: string | null): ProjectCreate {
  return { name: newProjectName(o), description: "", members: username ? [username] : [], template: "", init_git: false }
}

export function rowKey(o: OriginProject): string {
  return `${o.origin_fp}\u0000${o.origin_project_id}`
}

/** Nicht zugeordnete Ursprungsprojekte, gruppiert nach Instanz (Reihenfolge der API bleibt). */
export function groupUnassigned(origins: OriginProject[]): { instance: string; rows: OriginProject[] }[] {
  const groups = new Map<string, OriginProject[]>()
  for (const o of origins.filter(isUnassigned)) {
    const name = o.origin_name || o.origin_fp.slice(0, 12)
    groups.set(name, [...(groups.get(name) ?? []), o])
  }
  return [...groups.entries()].map(([instance, rows]) => ({ instance, rows }))
}
