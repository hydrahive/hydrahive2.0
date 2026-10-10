// Verknüpfte Projekte (docs/specs/linked-projects.md): Auswahl-Logik ohne React, damit sie testbar ist.
import type { Project } from "./types"

/** Projekte, die man verknüpfen kann: alle sichtbaren außer dem eigenen, alphabetisch. */
export function linkCandidates(all: Project[], selfId: string): Project[] {
  return all.filter((p) => p.id !== selfId).sort((a, b) => a.name.localeCompare(b.name))
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
