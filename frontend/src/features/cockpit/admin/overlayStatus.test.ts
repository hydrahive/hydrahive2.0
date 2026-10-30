// Plan docs/plans/farbstufen-kopffarben.md, Task 5: Zustand der Admin-Fenster aus Daten, die es schon gibt.
// Kein Zustand wird erfunden: ohne Befund kein Schild.
import { describe, expect, it } from "vitest"
import { jobsStatus, modulesStatus, nodesStatus, scheduledStatus } from "./overlayStatus"

describe("Zustand der Admin-Fenster", () => {
  it("Module: Ladefehler = fehler, Update verfügbar = warnung, sonst nichts", () => {
    expect(modulesStatus({ error: "kaputt", outdated: 2 })).toBe("fehler")
    expect(modulesStatus({ error: null, outdated: 2 })).toBe("warnung")
    expect(modulesStatus({ error: null, outdated: 0 })).toBeUndefined()
  })

  it("Jobs: fehlgeschlagene oder abgelaufene Jobs bzw. Ladefehler = fehler", () => {
    expect(jobsStatus({ error: null, failed: 1 })).toBe("fehler")
    expect(jobsStatus({ error: "x", failed: 0 })).toBe("fehler")
    expect(jobsStatus({ error: null, failed: 0 })).toBeUndefined()
  })

  it("Intervallaufgaben: letzter Lauf fehlgeschlagen = fehler", () => {
    expect(scheduledStatus({ error: null, failed: 3 })).toBe("fehler")
    expect(scheduledStatus({ error: null, failed: 0 })).toBeUndefined()
  })

  it("Nodes: offline = fehler, wartend = warnung, alle online = ok, keine Nodes = nichts", () => {
    expect(nodesStatus({ error: null, total: 3, online: 2, pending: 0, offline: 1 })).toBe("fehler")
    expect(nodesStatus({ error: null, total: 3, online: 2, pending: 1, offline: 0 })).toBe("warnung")
    expect(nodesStatus({ error: null, total: 2, online: 2, pending: 0, offline: 0 })).toBe("ok")
    expect(nodesStatus({ error: null, total: 0, online: 0, pending: 0, offline: 0 })).toBeUndefined()
    expect(nodesStatus({ error: "x", total: 2, online: 2, pending: 0, offline: 0 })).toBe("fehler")
  })
})
