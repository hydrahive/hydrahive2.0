// Föderations-Katalog (docs/specs/federation-catalog.md §Oberfläche): reine Hilfsfunktionen für
// den Abschnitt „Katalog-Sync“. Ohne React, damit sie direkt testbar sind.
import type { CatalogSettingsPatch } from "./api"
import type { CatalogSettings } from "./types"

export const INTERVAL_MIN = 60
export const INTERVAL_MAX = 3600

/** Bearbeitungsstand im Formular. Das Intervall bleibt Text, solange getippt wird. */
export interface CatalogDraft {
  enabled: boolean
  interval: string
  users: string[]
  excluded_projects: string[]
}

export function toDraft(s: CatalogSettings): CatalogDraft {
  return {
    enabled: s.enabled,
    interval: String(s.interval_seconds),
    users: [...s.users],
    excluded_projects: [...s.excluded_projects],
  }
}

/** Ganze Sekunden im erlaubten Bereich, sonst null (Backend prüft dasselbe: 60–3600). */
export function parseInterval(value: string): number | null {
  const v = value.trim()
  if (!/^\d+$/.test(v)) return null
  const n = Number(v)
  return n >= INTERVAL_MIN && n <= INTERVAL_MAX ? n : null
}

export function toggleIn(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter(x => x !== value) : [...list, value]
}

const sameSet = (a: string[], b: string[]) =>
  a.length === b.length && a.every(x => b.includes(x))

export function isDirty(draft: CatalogDraft, server: CatalogSettings): boolean {
  return draft.enabled !== server.enabled
    || draft.interval.trim() !== String(server.interval_seconds)
    || !sameSet(draft.users, server.users)
    || !sameSet(draft.excluded_projects, server.excluded_projects)
}

/** Body für PUT /catalog/settings oder null, wenn das Intervall ungültig ist. */
export function draftToPatch(draft: CatalogDraft): CatalogSettingsPatch | null {
  const interval = parseInterval(draft.interval)
  if (interval === null) return null
  return {
    enabled: draft.enabled,
    interval_seconds: interval,
    users: draft.users,
    excluded_projects: draft.excluded_projects,
  }
}
