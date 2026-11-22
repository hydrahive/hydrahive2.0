// Katalog-Reiter auf Clients (docs/specs/federation-shared-tasks.md §Oberfläche Cockpit):
// Filter-Logik und Query-Aufbau.
import { describe, expect, it } from "vitest"
import {
  EMPTY_FILTERS, formatDate, setKind, toMirrorQuery, toggleInstance, toggleStatus,
} from "./_catalogMirror"

describe("Filter: Instanz/Status togglen", () => {
  it("toggleInstance fügt hinzu und entfernt", () => {
    const f1 = toggleInstance(EMPTY_FILTERS, "fp1")
    expect(f1.instances).toEqual(["fp1"])
    expect(toggleInstance(f1, "fp1").instances).toEqual([])
  })
  it("toggleStatus fügt hinzu und entfernt", () => {
    const f1 = toggleStatus(EMPTY_FILTERS, "open")
    expect(f1.statuses).toEqual(["open"])
    expect(toggleStatus(f1, "open").statuses).toEqual([])
  })
})

describe("Art wechseln entfernt unpassende Status-Filter", () => {
  it("von „alle“ auf „task“: Idee-Status verschwindet", () => {
    const f = { ...EMPTY_FILTERS, statuses: ["open", "new"] }
    expect(setKind(f, "task").statuses).toEqual(["open"])
  })
  it("von „alle“ auf „idea“: Task-Status verschwindet", () => {
    const f = { ...EMPTY_FILTERS, statuses: ["open", "new"] }
    expect(setKind(f, "idea").statuses).toEqual(["new"])
  })
  it("zurück auf „alle“: Status bleiben erhalten", () => {
    const f = { ...EMPTY_FILTERS, kind: "task" as const, statuses: ["open"] }
    expect(setKind(f, null)).toEqual({ ...f, kind: null })
  })
})

describe("toMirrorQuery: Filter → API-Query", () => {
  it("leere Filter → nur limit/offset, keine leeren Listen", () => {
    expect(toMirrorQuery(EMPTY_FILTERS, 0)).toEqual({
      instance: undefined, project: undefined, status: undefined, kind: undefined, q: undefined,
      limit: 50, offset: 0,
    })
  })
  it("gesetzte Filter kommen 1:1 in die Query, Offset wird übernommen", () => {
    const f = { instances: ["fp1", "fp2"], project: "Hydrahive DEV", statuses: ["open"], kind: "task" as const, q: "foo" }
    expect(toMirrorQuery(f, 50)).toEqual({
      instance: ["fp1", "fp2"], project: "Hydrahive DEV", status: ["open"], kind: "task", q: "foo",
      limit: 50, offset: 50,
    })
  })
  it("Suchtext mit nur Leerzeichen gilt als leer", () => {
    expect(toMirrorQuery({ ...EMPTY_FILTERS, q: "   " }, 0).q).toBeUndefined()
  })
})

describe("formatDate", () => {
  it("null/leer → Platzhalter „noch nie“", () => {
    expect(formatDate(null, "noch nie")).toBe("noch nie")
    expect(formatDate(undefined, "noch nie")).toBe("noch nie")
  })
  it("ISO-Datum wird lokal formatiert (nicht roh übernommen)", () => {
    const out = formatDate("2026-11-21T10:00:00.000+00:00", "noch nie")
    expect(out).not.toBe("noch nie")
    expect(out).not.toContain("T10:00:00")
  })
})
