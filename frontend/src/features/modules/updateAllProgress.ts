// Zeilen des Ablaufs „Alle updaten“ → Fortschritt und Zusammenfassung (docs/specs/modul-update-alle.md).
// Format der Zeilen: core/src/hydrahive/modules/update_all.py.

export type UpdateAllPhase = "start" | "modules" | "build" | "restart" | "finished"

export interface UpdateAllProgress {
  phase: UpdateAllPhase
  done: number
  total: number
  ok: { id: string; from: string; to: string }[]
  failed: { id: string; reason: string }[]
  /** Es gab gar nichts zu tun. */
  upToDate: boolean
}

const OK = /^\[modules\] (\S+): fertig \((.+) → (.+)\)$/
const FAIL = /^\[modules\] (\S+): FEHLER – (.*)$/

export function parseUpdateAll(lines: string[], expectedTotal: number): UpdateAllProgress {
  const p: UpdateAllProgress = { phase: "start", done: 0, total: expectedTotal, ok: [], failed: [], upToDate: false }
  for (const line of lines) {
    let m: RegExpMatchArray | null
    if ((m = line.match(OK))) { p.ok.push({ id: m[1], from: m[2], to: m[3] }); p.phase = "modules" }
    else if ((m = line.match(FAIL))) { p.failed.push({ id: m[1], reason: m[2] }); p.phase = "modules" }
    else if (line.startsWith("[modules] update ")) p.phase = "modules"
    else if (line === "[modules] Frontend wird gebaut …") p.phase = "build"
    else if (line === "[modules] Neustart angefordert") p.phase = "restart"
    else if (line.startsWith("[modules] Fertig:")) p.phase = "finished"
    else if (line === "[modules] Alle Module sind aktuell") { p.phase = "finished"; p.upToDate = true }
  }
  p.done = p.ok.length + p.failed.length
  p.total = Math.max(p.total, p.done)
  return p
}
