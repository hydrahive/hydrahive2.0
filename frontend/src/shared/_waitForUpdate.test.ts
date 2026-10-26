import { describe, expect, it } from "vitest"
import { waitForUpdate, type UpdateProbe } from "./_waitForUpdate"

/** Ein Schritt je Takt (sleep): Health und Log sehen im selben Takt denselben Zustand. */
function probe(steps: Array<{ commit?: string | null; lines?: string[]; down?: boolean }>, start = 2): UpdateProbe {
  let i = -1
  const cur = () => steps[Math.min(Math.max(i, 0), steps.length - 1)]
  return {
    logTotal: async () => start,
    logSince: async () => { const s = cur(); if (s.down) throw new Error("down"); return s.lines ?? [] },
    health: async () => { const s = cur(); if (s.down) throw new Error("down"); return s.commit ?? "alt" },
    sleep: async () => { i++ },
  }
}

describe("Warten auf das Ende eines Updates", () => {
  it("neuer Commit → fertig", async () => {
    const r = await waitForUpdate(probe([{ commit: "alt" }, { down: true }, { commit: "neu" }]), "alt", 50)
    expect(r).toEqual({ kind: "done", commit: "neu" })
  })
  it("Schlusszeile ok ohne neuen Commit (nichts Neues) → fertig mit altem Stand, nicht 10 min warten", async () => {
    const r = await waitForUpdate(probe([{ commit: "alt", lines: ["x\n", "HH-UPDATE-ENDE: ok\n"] }]), "alt", 50)
    expect(r).toEqual({ kind: "done", commit: "alt" })
  })
  it("Schlusszeile fehler → fehlgeschlagen mit Grund", async () => {
    const r = await waitForUpdate(probe([{ lines: ["HH-UPDATE-ENDE: fehler npm ci fehlgeschlagen\n"] }]), "alt", 50)
    expect(r).toEqual({ kind: "failed", reason: "npm ci fehlgeschlagen" })
  })
  it("ok-Schlusszeile, Backend startet noch neu → wartet auf den neuen Commit", async () => {
    const r = await waitForUpdate(probe([
      { commit: "alt", lines: ["HH-UPDATE-ENDE: ok\n"] },
      { down: true },
      { commit: "neu", lines: ["HH-UPDATE-ENDE: ok\n"] },
    ]), "alt", 50, { settleChecks: 2 })
    expect(r).toEqual({ kind: "done", commit: "neu" })
  })
  it("ok-Schlusszeile, Server danach weg → erst „fertig“, wenn er wieder antwortet", async () => {
    let healthCalls = 0
    const steps = [
      { commit: "alt", lines: ["HH-UPDATE-ENDE: ok\n"] },
      { down: true }, { down: true }, { down: true }, { down: true },
      { commit: "alt", lines: ["HH-UPDATE-ENDE: ok\n"] },
    ]
    const base = probe(steps)
    const counting: UpdateProbe = { ...base, health: async () => { healthCalls++; return base.health() } }
    const r = await waitForUpdate(counting, "alt", 50, { settleChecks: 2 })
    expect(r).toEqual({ kind: "done", commit: "alt" })
    expect(healthCalls).toBe(6)                    // erst im 6. Takt (Server wieder da), nicht während er weg war
  })
  it("weder Commit noch Schlusszeile → Zeitüberschreitung", async () => {
    const r = await waitForUpdate(probe([{ commit: "alt", lines: ["läuft\n"] }]), "alt", 5)
    expect(r).toEqual({ kind: "failed", reason: "timeout" })
  })
  it("Server weg und Log nicht lesbar → weiter warten (kein Fehlalarm)", async () => {
    const r = await waitForUpdate(probe([{ down: true }, { down: true }, { commit: "neu" }]), "alt", 50)
    expect(r).toEqual({ kind: "done", commit: "neu" })
  })
})

// docs/specs/system-updates.md: Das Update hebt jetzt auch Systempakete an – das dauert länger als 10 min.
import { UPDATE_MAX_CHECKS } from "./_waitForUpdate"
describe("Wartezeit des Update-Fensters", () => {
  it("höchstens 30 Minuten (bei 3 s Takt)", () => {
    expect(UPDATE_MAX_CHECKS * 3).toBe(30 * 60)
  })
})
