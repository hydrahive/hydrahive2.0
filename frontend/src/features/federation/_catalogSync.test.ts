// Föderations-Katalog Etappe 1 (docs/specs/federation-catalog.md): Formular-Logik „Katalog-Sync“.
import { describe, expect, it } from "vitest"
import { draftToPatch, isDirty, parseInterval, toDraft, toggleIn } from "./_catalogSync"
import type { CatalogSettings } from "./types"

const base: CatalogSettings = {
  enabled: false, interval_seconds: 300, users: [], excluded_projects: [],
  hub: null, accepting_from: [],
  last_push_at: null, last_ok_at: null, last_full_at: null, last_error: null,
}

describe("Intervall wie im Backend (60–3600 s, ganze Zahl)", () => {
  it.each(["60", "300", "3600", " 120 "])("gültig: %s", v => {
    expect(parseInterval(v)).toBe(Number(v.trim()))
  })
  it.each(["59", "3601", "0", "", "abc", "12.5", "-60", "1e3"])("ungültig: %s", v => {
    expect(parseInterval(v)).toBeNull()
  })
})

describe("Entwurf und Speichern", () => {
  it("Standard: aus, Nutzerliste leer, nichts geändert", () => {
    const d = toDraft(base)
    expect(d).toEqual({ enabled: false, interval: "300", users: [], excluded_projects: [] })
    expect(isDirty(d, base)).toBe(false)
  })
  it("Änderung an Schalter, Intervall, Nutzern oder Projekten ist ungespeichert", () => {
    const d = toDraft(base)
    expect(isDirty({ ...d, enabled: true }, base)).toBe(true)
    expect(isDirty({ ...d, interval: "600" }, base)).toBe(true)
    expect(isDirty({ ...d, users: ["till"] }, base)).toBe(true)
    expect(isDirty({ ...d, excluded_projects: ["p1"] }, base)).toBe(true)
  })
  it("Reihenfolge der Nutzer zählt nicht als Änderung", () => {
    const s = { ...base, users: ["a", "b"] }
    expect(isDirty({ ...toDraft(s), users: ["b", "a"] }, s)).toBe(false)
  })
  it("Body für PUT nur mit gültigem Intervall", () => {
    const d = { enabled: true, interval: "900", users: ["till"], excluded_projects: ["p1"] }
    expect(draftToPatch(d)).toEqual({ enabled: true, interval_seconds: 900, users: ["till"], excluded_projects: ["p1"] })
    expect(draftToPatch({ ...d, interval: "30" })).toBeNull()
  })
  it("toggleIn fügt hinzu und entfernt", () => {
    expect(toggleIn(["a"], "b")).toEqual(["a", "b"])
    expect(toggleIn(["a", "b"], "a")).toEqual(["b"])
  })
  it("toDraft kopiert die Listen (keine geteilte Referenz)", () => {
    const s = { ...base, users: ["a"] }
    const d = toDraft(s)
    d.users.push("b")
    expect(s.users).toEqual(["a"])
  })
})
