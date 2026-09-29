// Reine Hilfsfunktionen für die Freigabe-Tabelle (ohne React), damit sie testbar sind.
import type { AccessCatalog, AccessLevel, CatalogCapability, SubjectType } from "./types"

export interface MatrixSubject {
  key: string
  type: SubjectType
  id: string
  label: string
}

export function subjectsFor(catalog: AccessCatalog): MatrixSubject[] {
  return [
    { key: "everyone:", type: "everyone", id: "", label: "" },
    ...catalog.groups.map((g) => ({ key: `group:${g.id}`, type: "group" as const, id: g.id, label: g.name })),
    ...catalog.users.map((u) => ({ key: `user:${u.user_id}`, type: "user" as const, id: u.user_id, label: u.username })),
  ]
}

export function cellLevel(cap: CatalogCapability, type: SubjectType, id: string): AccessLevel | null {
  const hit = cap.grants.find((g) => g.subject_type === type && g.subject_id === id)
  return hit ? hit.level : null
}

export function nextLevel(current: AccessLevel | null): AccessLevel | null {
  if (current === null) return "use"
  if (current === "use") return "manage"
  return null
}

export interface CapabilityGroup {
  module_id: string
  items: CatalogCapability[]
}

export function groupCapabilities(caps: CatalogCapability[]): CapabilityGroup[] {
  const out: CapabilityGroup[] = []
  for (const cap of caps) {
    const last = out[out.length - 1]
    if (last && last.module_id === cap.module_id) last.items.push(cap)
    else out.push({ module_id: cap.module_id, items: [cap] })
  }
  return out
}
