import { updateOutcome } from "./_updateLogStatus"

/** Was das Update-Fenster zum Warten braucht – als Schnittstelle, damit es ohne Server testbar ist. */
export interface UpdateProbe {
  /** Zeilenzahl des Update-Logs JETZT (vor dem Start). */
  logTotal: () => Promise<number>
  /** Log-Zeilen ab Zeile `since`. Wirft, wenn der Server gerade weg ist. */
  logSince: (since: number) => Promise<string[]>
  /** Aktueller Commit laut /health. Wirft, wenn der Server gerade weg ist. */
  health: () => Promise<string | null>
  sleep: (ms: number) => Promise<void>
}

export type WaitResult = { kind: "done"; commit: string | null } | { kind: "failed"; reason: string }

/** Wartet auf das Ende eines Updates.
 *
 *  Fertig, sobald (a) ein neuer Commit läuft oder (b) das Update-Skript „HH-UPDATE-ENDE: ok“ geschrieben hat und
 *  das Backend danach wieder antwortet – auch ohne neuen Commit (nichts Neues, Rebuild). „HH-UPDATE-ENDE: fehler“
 *  meldet sofort den Grund. Früher wartete das Fenster nur auf (a), bei „nichts Neues“ 10 min (Befund 22.10.2026).
 */
export async function waitForUpdate(
  p: UpdateProbe, oldCommit: string | null, maxChecks: number,
  opts: { intervalMs?: number; settleChecks?: number } = {},
): Promise<WaitResult> {
  const interval = opts.intervalMs ?? 3000
  // Nach „ok“ kurz weiter prüfen: Das Backend startet ggf. gerade neu und meldet dann den neuen Commit.
  const settle = opts.settleChecks ?? 3
  let start = 0
  try { start = await p.logTotal() } catch { /* Log nicht lesbar – dann eben ab Anfang */ }
  let okSeen = -1
  for (let i = 0; i < maxChecks; i++) {
    await p.sleep(interval)
    let commit: string | null | undefined
    try { commit = await p.health() } catch { commit = undefined }
    if (commit && commit !== oldCommit) return { kind: "done", commit }
    let lines: string[] | null
    try { lines = await p.logSince(start) } catch { lines = null }
    if (lines) {
      const o = updateOutcome(lines, 0)
      if (o.kind === "error") return { kind: "failed", reason: o.reason }
      if (o.kind === "ok" && okSeen < 0) okSeen = i
    }
    if (okSeen >= 0 && commit !== undefined && i - okSeen >= settle - 1) return { kind: "done", commit: commit ?? oldCommit }
  }
  return { kind: "failed", reason: "timeout" }
}
