import { describe, expect, it } from "vitest"
import { shouldAutoClose, type DeleteJob } from "./api"

const job = (p: Partial<DeleteJob>): DeleteJob => ({
  id: "j1", kind: "agent", target: "a1", name: "Spezi", mode: "archive", state: "running", step: "pack",
  error: null, bytes_total: 0, bytes_done: 0, files_total: 0, packages: [], leftovers: [], ...p,
})

describe("shouldAutoClose (autoCloseOnDone-Prop von DeleteDialog)", () => {
  it("schließt bei state=done, wenn autoCloseOnDone gesetzt ist", () => {
    expect(shouldAutoClose(true, job({ state: "done" }))).toBe(true)
  })

  it("schließt NICHT bei state=failed, auch mit autoCloseOnDone — Fehler soll sichtbar bleiben", () => {
    expect(shouldAutoClose(true, job({ state: "failed" }))).toBe(false)
  })

  it("schließt nicht, solange der Auftrag noch läuft", () => {
    expect(shouldAutoClose(true, job({ state: "running" }))).toBe(false)
    expect(shouldAutoClose(true, job({ state: "queued" }))).toBe(false)
  })

  it("ohne autoCloseOnDone (Default false, andere Aufrufer) schließt nie automatisch", () => {
    expect(shouldAutoClose(false, job({ state: "done" }))).toBe(false)
  })

  it("ohne Job (noch nicht gestartet) schließt nie automatisch", () => {
    expect(shouldAutoClose(true, null)).toBe(false)
  })
})
