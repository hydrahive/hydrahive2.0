/* Wann die Statusleiste der Hintergrund-Aufträge neu abfragt.
   Reine Funktionen, damit die Regeln ohne Browser testbar sind. */

export const POLL_MS = 5000

/** Nach dem Ende eines eigenen Laufs noch so lange weiter abfragen. Ein
 *  ask_agent ist oft die LETZTE Aktion eines Laufs; die Abfrage beim
 *  Lauf-Ende kann ihn knapp verpassen (Befund 01.10.2026: Leiste erst
 *  nach F5 sichtbar). */
export const AFTER_RUN_GRACE_MS = 15000

export interface PollInput {
  hasSession: boolean
  running: number
  busy: boolean
  /** Zeitpunkt (ms), zu dem busy zuletzt von true auf false ging, sonst null. */
  runEndedAt: number | null
  now: number
}

export function shouldPoll(i: PollInput): boolean {
  if (!i.hasSession) return false
  if (i.running > 0 || i.busy) return true
  return i.runEndedAt !== null && i.now - i.runEndedAt < AFTER_RUN_GRACE_MS
}

/** Ein Live-Sync-Ping (Lauf startet/endet, auch auf anderem Gerät) ist ein
 *  Anlass, sofort neu zu laden — nicht erst beim nächsten Intervall. */
export function isRefreshPing(kind: string): boolean {
  return kind === "start" || kind === "done"
}
