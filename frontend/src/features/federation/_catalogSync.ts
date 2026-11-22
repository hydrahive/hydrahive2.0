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
  /** Gemeinsame Taskpflege (docs/specs/federation-shared-tasks.md §Schalter). */
  shared: boolean
  remote_edits: boolean
}

export function toDraft(s: CatalogSettings): CatalogDraft {
  return {
    enabled: s.enabled,
    interval: String(s.interval_seconds),
    users: [...s.users],
    excluded_projects: [...s.excluded_projects],
    shared: s.shared,
    remote_edits: s.remote_edits,
  }
}

/** ``remote_edits`` ergibt ohne ``shared`` keinen Sinn — Ausschalten von ``shared``
 * nimmt ``remote_edits`` mit (docs/specs/federation-shared-tasks.md §Schalter). */
export function setShared(draft: CatalogDraft, shared: boolean): CatalogDraft {
  return { ...draft, shared, remote_edits: shared ? draft.remote_edits : false }
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
    || draft.shared !== server.shared
    || draft.remote_edits !== server.remote_edits
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
    shared: draft.shared,
    remote_edits: draft.shared ? draft.remote_edits : false,
  }
}

/** Codes aus ``last_error`` (Backend, kommagetrennt) → Text-ID unter ``catalog.reason``.
 *  ``source_failed:idea`` zählt als ``source_failed``. Unbekannte Codes bleiben roh (textId null). */
export const REASON_CODES = [
  "peer_catalog_not_accepted", "hub_unreachable", "peer_unknown", "peer_signature_invalid", "peer_expired",
  "peer_rate_limited", "peer_replay", "peer_payload_too_large", "hub_bad_ack", "sync_failed", "source_failed",
] as const

export function reasonTexts(lastError: string | null): { textId: string | null; raw: string }[] {
  if (!lastError) return []
  return lastError.split(",").map(s => s.trim()).filter(Boolean).map(raw => {
    const base = raw.split(":")[0]
    return { textId: (REASON_CODES as readonly string[]).includes(base) ? `catalog.reason.${base}` : null, raw }
  })
}

/** Codes aus ``last_pull_error`` (Abholen der Kopie, docs/specs/federation-shared-tasks.md
 *  §Schalter/§Nachricht catalog_pull). Anders als beim Push nur ein einzelner Code, kein
 *  Komma-String. Unbekannter Code → allgemeiner Text mit dem Code (gleiches Muster wie
 *  ``reasonTexts``, aber hier immer ein Text, nie der rohe Code allein). */
export const PULL_REASON_CODES = [
  "peer_catalog_not_shared", "peer_catalog_not_accepted", "hub_unreachable", "peer_signature_invalid",
  "peer_replay", "hub_bad_ack", "hub_bad_reply", "peer_payload_too_large", "pull_failed", "http_404",
] as const

export function pullReasonText(code: string): { textId: string; code: string } {
  const known = (PULL_REASON_CODES as readonly string[]).includes(code)
  return { textId: known ? `catalog.pull_reason.${code}` : "catalog.pull_reason.unknown", code }
}
