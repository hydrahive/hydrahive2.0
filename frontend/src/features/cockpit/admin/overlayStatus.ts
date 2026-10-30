import type { BoxStatus } from "@/shared/brand/boxLook"

/**
 * Zustand der Admin-Fenster aus Daten, die das Fenster ohnehin lädt (Plan farbstufen-kopffarben, Task 5).
 * Ohne Befund: undefined → kein Schild, die Kopffarbe bleibt.
 */

export function modulesStatus(s: { error: string | null; outdated: number }): BoxStatus | undefined {
  if (s.error) return "fehler"
  return s.outdated > 0 ? "warnung" : undefined
}

export function jobsStatus(s: { error: string | null; failed: number }): BoxStatus | undefined {
  return s.error || s.failed > 0 ? "fehler" : undefined
}

export function scheduledStatus(s: { error: string | null; failed: number }): BoxStatus | undefined {
  return s.error || s.failed > 0 ? "fehler" : undefined
}

export function nodesStatus(s: { error: string | null; total: number; online: number; pending: number; offline: number }): BoxStatus | undefined {
  if (s.error || s.offline > 0) return "fehler"
  if (s.pending > 0) return "warnung"
  return s.total > 0 && s.online === s.total ? "ok" : undefined
}
