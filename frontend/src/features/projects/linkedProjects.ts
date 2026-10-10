// Verknüpfte Projekte (docs/specs/linked-projects.md): Auswahl-Logik ohne React, damit sie testbar ist.
import type { Project } from "./types"

export interface LinkUser { username: string | null; role: string | null }

/** Darf ``user`` das Projekt verknüpfen? Wie der Server: System-Admin immer, sonst mindestens ``write``. */
function canLink(p: Project, user: LinkUser): boolean {
  if (user.role === "admin") return true
  if (!user.username) return false
  if (p.created_by === user.username) return true
  const m = (p.members ?? []).find((x) => x.username === user.username)
  return m?.role === "write" || m?.role === "admin"
}

/** Projekte zur Auswahl: andere Projekte mit Schreibrecht, plus bereits verknüpfte (zum Abwählen), alphabetisch. */
export function linkCandidates(all: Project[], selfId: string, user: LinkUser, linked: string[]): Project[] {
  return all.filter((p) => p.id !== selfId && (canLink(p, user) || linked.includes(p.id)))
    .sort((a, b) => a.name.localeCompare(b.name))
}

/** Auswahl umschalten (Reihenfolge der Auswahl bleibt). */
export function toggleLink(current: string[], id: string): string[] {
  return current.includes(id) ? current.filter((x) => x !== id) : [...current, id]
}

/** Geändert gegenüber dem gespeicherten Stand? (Reihenfolge egal) */
export function linksChanged(saved: string[], draft: string[]): boolean {
  if (saved.length !== draft.length) return true
  const s = new Set(saved)
  return draft.some((x) => !s.has(x))
}
